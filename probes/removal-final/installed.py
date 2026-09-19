"""Final tool, retained installed default, new scratch sessions, no compilation."""
from pathlib import Path
import os,sys,json,subprocess as sp,importlib.util,select,time,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target/installed';assert not W.exists();W.mkdir();O=B/'results/removal-final-0066/installed';O.mkdir(exist_ok=True)
E=json.loads((B/'probes/removal-storage/target/real/env.json').read_text());E.update(RNX_PROJECT_TOOL=str(H/'target/tool-ordinary'),XDG_STATE_HOME=str(W/"state ' private"),RNX_HISTORY=str(W/'history'));E.pop('RNX_DEP_RUNTIME',None)
(W/'traps').mkdir();log=W/'compile.log';log.touch()
for name in ['cargo','rustc']:
 real=shutil.which(name);p=W/'traps'/name;p.write_text('#!/usr/bin/python3\nimport os,sys\na=sys.argv[1:]\nif '+repr(name)+'=="cargo" and "build" in a or '+repr(name)+'=="rustc" and "--crate-name" in a and not any(v.startswith("--print") for v in a):\n open('+repr(str(log))+',"a").write("compile\\n")\n raise SystemExit(91)\nos.execv('+repr(real)+',['+repr(real)+',*a])\n');p.chmod(0o755)
E['PATH']=str(W/'traps')+':'+E['PATH']
for name,args in [('cargo',['build']),('rustc',['--crate-name','control'])]:assert sp.run([str(W/'traps'/name),*args],env=E).returncode==91
assert sp.run([str(W/'traps/rustc'),'--crate-name','control','--print=cfg'],env=E,capture_output=True).returncode==0
log.write_text('')
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
term=load('terminal',B/'probes/project-interactive/common.py');Cluster=load('cluster',B/'probes/postgres/cluster.py').Cluster
rows=[]
def until(t,needle):
 out='';end=time.monotonic()+45
 while time.monotonic()<end:
  if select.select([t.master],[],[],.1)[0]:
   b=os.read(t.master,65536);t.log+=b;out+=term.text(b)
   if needle in out:return out
 raise AssertionError((needle,out))
with Cluster() as cluster:
 for i in range(2):
  t=term.Terminal([R/'target/release/rnx','--no-splash','--color=never'],W,E)
  try:
   t.read();os.write(t.master,b':dep --offline polars postgres\n');notice=until(t,'Continue? [y/N]');assert 'Runtime: installation ' in notice
   os.write(t.master,b'y\n');out=until(t,'[1] >');assert 'restart is beginning' in out
   assert 'true' in t.send('polars::lit(1).is_ok()')
   s='let row = postgres::query('+json.dumps(cluster.url)+', "SELECT $1::int8 AS n", [42], #{}).await.unwrap();'
   assert 'error at input' not in t.send(s)
   assert 'error' not in t.send('assert!(row.rows[0].n == 42);').lower()
   artifact=Path('/proc',str(t.p.pid),'exe').resolve();os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=10)==0;cluster.wait_idle()
   assert not log.read_text();rows.append(dict(session=i,artifact=str(artifact),typed_query=True,polars=True,compilation_trapped=True,pid=t.p.pid))
   (O/(str(i)+'.pty')).write_bytes(t.log)
  finally:
   (O/(str(i)+'.pty')).write_bytes(t.log);t.close()
 pid=cluster.postmaster
assert not Path('/proc',str(pid)).exists() and all(not Path('/proc',str(r['pid'])).exists() for r in rows)
(O/'results.json').write_text(json.dumps(dict(sessions=rows,postmaster_reaped=True),indent=2)+'\n');print('PASS final-tool installed :dep with compiler traps and typed SQL')
