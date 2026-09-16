#!/usr/bin/env python3
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import sys
sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
BENCH = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / 'postgres'))
sys.path.insert(0, str(HERE.parent / 'server-transactions'))
from cluster import Cluster
from proxy import Proxy
OUT = BENCH / 'results/commit-classification-0056'
OUT.mkdir(parents=True, exist_ok=True)

def execute(args, env=None):
    proc = subprocess.Popen(args, cwd=HERE, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=120)
    except BaseException:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        raise
    if proc.returncode:
        raise RuntimeError(f'{args}: {proc.returncode}\n{stdout}\n{stderr}')
    return stdout, stderr

execute(['cargo', 'build', '--offline', '--locked', '--quiet'])
binary = HERE / 'target/debug/rnx-commit-classification-probe'
rows=[]
for repeat in (1, 2):
    with Cluster() as cluster:
        postmaster=cluster.postmaster
        for mode in ('deferred', 'serialization', 'deadlock', 'unclassified'):
            proxy=Proxy(cluster.root / ('proxy-' + mode), cluster.root)
            try:
                env={k:v for k,v in os.environ.items() if not k.startswith('PG')}
                env['RNX_COMMIT_URL']=f'postgresql:///postgres?host={proxy.path}&application_name=commit-probe'
                stdout, stderr=execute([str(binary),mode], env)
                assert not stderr, stderr
                result=json.loads(stdout)
                commits=[e for e in proxy.events if e.get('pid')==result['victim_pid'] and e.get('sql')=='COMMIT']
                assert len(commits)==1, proxy.events
                result.update(repeat=repeat,commit_attempts=len(commits))
                # Observe all probe backends gone independently after all joined drivers.
                assert cluster.sql("SELECT count(*) FROM pg_stat_activity WHERE application_name='commit-probe'").stdout.strip()=='0'
                result['backends_after']=0
                rows.append(result)
                (OUT/f'{repeat}-{mode}.json').write_text(json.dumps({'result':result,'wire':proxy.events},indent=2)+'\n')
            finally:
                proxy.close()
        events=cluster.events
    assert not pathlib.Path(f'/proc/{postmaster}').exists()
    (OUT/f'{repeat}-cluster.json').write_text(json.dumps({'postmaster_reaped':postmaster,'events':events},indent=2)+'\n')
(OUT/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
meta=json.loads(execute(['cargo','metadata','--locked','--offline','--format-version','1'])[0])
conditions={'rustc':execute(['rustc','--version'])[0].strip(), 'postgres':execute(['/usr/lib/postgresql/18/bin/postgres','--version'])[0].strip(),
            'hashes':{str(p.relative_to(BENCH)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/'src/main.rs',HERE/'Cargo.lock',HERE/'run.py',HERE.parent/'server-transactions/proxy.py',HERE.parent/'postgres/cluster.py',binary]},
            'packages':[{'name':p['name'],'version':p['version'],'license':p['license']} for p in meta['packages']]}
(OUT/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
print(json.dumps(rows,indent=2))
