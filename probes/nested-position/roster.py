"""Eligible real ignored build output, explicit GIT_EDITOR fallback, shared checks."""
from pathlib import Path
import os,json,subprocess as sp,collections,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/nested-position-0065';T=B.parent/'rnx/tools/project/target/debug/rnx-project-assembly-probe'
p=B/'probes/native-inventory/target/s';target=p/'adapters/polars/target';assert not target.exists()
E=json.loads((B/'probes/inventory-workflow/target/env.json').read_text());assert not any(k.startswith('GIT_') for k in E)
rows=[]
def pair(name,n,env):
 roots=[p]+[p/'adapters'/a for a in ['polars','postgres','pgcopy'][:n]];data=[]
 for candidate in [False,True]:
  q=W/'roster-config.json';q.write_text(json.dumps(dict(roots=list(map(str,roots)),candidate=candidate,entries=100000,bytes=512*1024*1024)))
  run=sp.run([T,'nested-inventory',q],env=env,capture_output=True,text=True,timeout=60);assert run.returncode==0,run.stderr;data.append(json.loads(run.stdout))
 assert data[0]['answer']==data[1]['answer'] and 'Ok' in data[1]['answer']
 assert data[0]['remaining_bytes']==data[1]['remaining_bytes']
 events=data[1]['events'];calls=sum('git' in e for e in events);checks=sum('shared_check' in e for e in events);reads=collections.Counter(e['read'] for e in events if 'read' in e)
 if 'GIT_EDITOR' in env:assert calls==3*(n+1) and checks==0
 else:assert calls==3 and checks==int(n>0) and set(reads.values())=={1}
 rows.append(dict(case=name,count=n,git=calls,shared_checks=checks,physical_reads=sum(reads.values()),oracle=data[0],candidate=data[1]));print('PASS',name,n,calls,checks,flush=True)
try:
 target.mkdir()
 for n in range(14000):(target/str(n)).touch()
 assert sp.run(['git','-C',p,'check-ignore',str(target/'0')],env=E,stdout=sp.DEVNULL).returncode==0
 for n in range(4):pair('ignored-build-14000',n,E)
 for n in [1,3]:pair('GIT_EDITOR-fallback',n,E|{'GIT_EDITOR':'true'})
finally:shutil.rmtree(target)
(O/'roster.json').write_text(json.dumps(rows,indent=2)+'\n')
