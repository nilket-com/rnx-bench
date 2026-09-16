"""Interrupt the fixture during initdb, server start and a running query."""
import json, os, pathlib, signal, subprocess, sys, tempfile, time
from cluster import Cluster
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/postgres-0052-adapter';OUT.mkdir(exist_ok=True,parents=True)
if len(sys.argv)>1:
    case=sys.argv[1]; c=Cluster()
    try:
        with c:
            if case=='failure': raise RuntimeError('deliberate fixture failure')
            if case=='query': c.sql('SELECT pg_sleep(120)')
    except (KeyboardInterrupt,RuntimeError) as e:
        print(type(e).__name__,str(e),flush=True)
    finally:
        pathlib.Path(os.environ['RNX_PG_REPORT']).write_text(json.dumps(dict(events=c.events,root=str(c.root),postmaster=c.postmaster)))
    sys.exit(0)

results={}
# Other PostgreSQL fixtures are not running during this cleanup battery.
for p in pathlib.Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:args=(p/'cmdline').read_bytes()
    except (FileNotFoundError,PermissionError):continue
    assert not (args.startswith(b'/usr/lib/postgresql/18/bin/postgres\0') and b'rnx-pg-contract-' in args),args
with tempfile.TemporaryDirectory(prefix='rnx-pg-cleanup-observer-') as directory:
    directory=pathlib.Path(directory)
    for case in ['success','failure','initdb','startup','query']:
        stage=directory/(case+'.stage'); report=directory/(case+'.json')
        p=subprocess.Popen([sys.executable,__file__,case],env=dict(os.environ,RNX_PG_STAGE_FILE=str(stage),RNX_PG_REPORT=str(report)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        observed=None
        try:
            if case in ['initdb','startup','query']:
                deadline=time.monotonic()+10
                while time.monotonic()<deadline:
                    try: observed=json.loads(stage.read_text())
                    except (FileNotFoundError,json.JSONDecodeError):time.sleep(.001);continue
                    desired={'initdb':'initdb','startup':'pg_ctl','query':'psql'}[case]
                    if observed['stage']==desired:
                        if case=='startup' and not (pathlib.Path(observed['data'])/'postmaster.pid').exists():
                            time.sleep(.001);continue
                        if case=='query':
                            # Skip the initial CREATE ROLE; wait until the child
                            # psql command line identifies the sleeping query.
                            try:args=pathlib.Path(f"/proc/{observed['pid']}/cmdline").read_bytes()
                            except FileNotFoundError:time.sleep(.001);continue
                            if b'pg_sleep(120)' not in args:time.sleep(.001);continue
                        assert pathlib.Path(f"/proc/{observed['pid']}").exists(),observed
                        p.send_signal(signal.SIGINT);break
                    time.sleep(.001)
                else:raise AssertionError((case,observed))
            stdout,stderr=p.communicate(timeout=15)
            assert p.returncode==0,(case,stdout,stderr)
            r=json.loads(report.read_text());assert not pathlib.Path(r['root']).exists(),r
            for event in r['events']:
                assert not pathlib.Path(f"/proc/{event['pid']}").exists(),event
            if r['postmaster']:assert not pathlib.Path(f"/proc/{r['postmaster']}").exists(),r
            results[case]=dict(observed=observed,report=r,stdout=stdout,stderr=stderr)
        finally:
            if p.poll() is None:p.kill();p.communicate()
(OUT/'cleanup.json').write_text(json.dumps(results,indent=2)+'\n')
print('cleanup proved after success, failure, initdb SIGINT, startup SIGINT and query SIGINT')
