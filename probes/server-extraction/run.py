#!/usr/bin/env python3
"""Run unchanged acceptance assertions against the extracted public-API server."""
import argparse, json, os, pathlib, signal, subprocess, sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent
BENCH=HERE.parents[1]
ROOT=BENCH.parent/'rnx'
PACKAGE=ROOT/'servers/http-postgres'
sys.path.insert(0,str(HERE.parent/'postgres'))
from cluster import Cluster

def command(args,env,log):
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w') as output:
        p=subprocess.Popen(args,cwd=BENCH,env=env,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            code=p.wait(timeout=600)
        except BaseException:
            os.killpg(p.pid,signal.SIGKILL);p.wait();raise
        if code:raise RuntimeError(f'exit {code}: {log}')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['wire','transactions','shutdown-int','shutdown-term','scheduling']);ap.add_argument('--output',type=pathlib.Path,default=BENCH/'results/server-extraction-0056');a=ap.parse_args()
    out=a.output.resolve();env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',RNX_SERVER_BINARY=str(PACKAGE/'target/release/rnx-http-postgres'),RNX_SERVER_PROGRAM=str(PACKAGE/'examples/fixture.rn'))
    # An interrupted/failed rerun must not leave an old aggregate looking current.
    (out/a.stage/'results.json').unlink(missing_ok=True)
    if a.stage=='wire':args=['probes/server-shutdown/regression.py','--output',str(out/'wire')]
    elif a.stage=='transactions':args=['probes/server-transactions/transactions.py','--output',str(out/'transactions')]
    elif a.stage.startswith('shutdown-'):args=['probes/server-shutdown/shutdown.py','--signal',a.stage.split('-')[1].upper(),'--output',str(out/a.stage)]
    else:
        cpus=sorted(os.sched_getaffinity(0))[:4];assert len(cpus)==4
        with Cluster() as c:
            c.sql('CREATE TABLE audit(tag text NOT NULL)');env['RNX_POOL_URL']=c.url
            args=['probes/server-http/scheduling.py','--samples','3','--cpus',','.join(map(str,cpus[:3])),'--client-cpu',str(cpus[3]),'--output',str(out/'scheduling')]
            command([sys.executable,*args],env,out/'scheduling.log')
            assert c.sql("SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE 'rnx-pool-%'").stdout.strip()=='0'
        return
    command([sys.executable,*args],env,out/(a.stage+'.log'))
if __name__=='__main__':main()
