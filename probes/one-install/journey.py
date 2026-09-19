from common import *
import select,re,shlex
kind=sys.argv[1];D=T/kind;setup,E=environment(kind);exe=Path(setup['exe']);OUT=O/kind;OUT.mkdir();cwd=D/'caller';cwd.mkdir();rows={};pids=[]
term=load('terminal',B/'probes/project-interactive/common.py');Cluster=load('cluster',B/'probes/postgres/cluster.py').Cluster
assert not Path(setup['fixture_source']).exists();assert not (Path(E['CARGO_HOME'])/'git').exists();assert not Path(E['XDG_DATA_HOME']).exists();assert not Path(E['RNX_PROJECT_CACHE']).exists()
def save_rows():(OUT/'journey.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
def until(t,needle,timeout=30):
 out='';end=time.monotonic()+timeout
 while time.monotonic()<end:
  if select.select([t.master],[],[],.1)[0]:
   b=os.read(t.master,65536);t.log+=b;out+=term.text(b)
   if needle in out:return out
 raise AssertionError((needle,out))
def start(env=E,args=None):
 t=term.Terminal(args or [exe,'--no-splash','--color=never'],cwd,env);t.read();pids.append(t.p.pid);return t

def close(t,label,eof=False):
 try:
  os.write(t.master,b'\x04' if eof else b':quit\n');t.read(False);assert t.p.wait(timeout=10)==0
 finally:(OUT/(label+'.pty')).write_bytes(t.log);t.close()

def cleanup(t,label):
 (OUT/(label+'.pty')).write_bytes(t.log)
 if t.p.poll() is None:t.close()
def dep(t,names,offline=False,decline=False,pid=None):
 request=':dep '+('--offline ' if offline else '')+names;os.write(t.master,(request+'\n').encode());notice=until(t,'Continue? [y/N]')
 assert 'bindings and declarations will be lost' in notice
 os.write(t.master,b'n\n' if decline else b'y\n');start_time=time.monotonic();out=t.read(timeout=1800)
 if decline:return notice,out,0
 assert 'restart is beginning' in out and re.search(r'\[1\] > \r*$',out),out
 if pid is not None:assert Path('/proc',str(pid)).exists() and Path('/proc',str(pid),'exe').resolve().parent.name=='artifacts'
 assert not Path('/proc',str(pid or t.p.pid),'task',str(pid or t.p.pid),'children').read_text().strip()
 return notice,out,time.monotonic()-start_time

def reopen(out):
 line=out.split('Reopen this scratch session:\r\n',1)[1].split('\r\n',1)[0].strip();args=shlex.split(line);assert args[:3]==[str(exe),'project','session'];return line,Path(args[-1])
def identity(pid):
 artifact=Path('/proc',str(pid),'exe').resolve();return {'artifact':str(artifact),'key':artifact.parent.parent.name,'sha256':sha(artifact)}
def frame(t,prefix):
 lines=[f'fs::write_new("{prefix}.csv", "category,value\\na,1\\na,2\\n🦀,3\\n🦀,4\\nmissing,\\n").unwrap();',f'let frame = polars::read_csv("{prefix}.csv", [("category","string"),("value","i64")]).unwrap();','let grouped=frame.lazy().filter(polars::col("value").gt(polars::lit(1).unwrap())).group_by([polars::col("category")]).unwrap();','let plan=grouped.agg([polars::col("value").sum().alias("total")]).unwrap().sort(["category"]).unwrap();','let result=plan.collect().unwrap();']
 for line in lines:assert 'error at input' not in t.send(line)
 shown=t.send('println!("{}",result.preview().unwrap());');assert '"a" | 2' in shown and '"🦀" | 7' in shown,shown
 error=t.send('frame.lazy().sort(["missing"]).unwrap().collect()');assert 'Err' in error and 'missing' in error
 assert '5 rows' in t.send('println!("{}",frame.preview().unwrap());')
 assert 'error' not in t.send(f'result.write_parquet_new("{prefix}.parquet").unwrap();').lower()
 assert 'error' not in t.send(f'assert!(polars::read_parquet("{prefix}.parquet").unwrap().preview().unwrap()==result.preview().unwrap());').lower()
 return shown
# Preserve the actual compilation log, including explicit positive traps.
traps=D/'traps';traps.mkdir();log=D/'compilation.jsonl'
for name in ['cargo','rustc']:
 actual=shutil.which(name,path=E['PATH']);f=traps/name
 f.write_text('#!/usr/bin/python3\nimport os,sys,json\na=sys.argv[1:]\nc=("build" in a or "rustc" in a) if '+repr(name)+'=="cargo" else ("--crate-name" in a and not any(x.startswith("--print") for x in a))\nif c:\n with open(os.environ["ONE_INSTALL_COMPILE_LOG"],"a") as f:f.write(json.dumps(sys.argv)+"\\n")\n if os.getenv("ONE_INSTALL_FORBID_COMPILE")=="1":sys.exit(91)\nos.execv('+repr(actual)+',['+repr(actual)+',*a])\n');f.chmod(0o700)
logged=E|{'PATH':str(traps)+':'+E['PATH'],'ONE_INSTALL_COMPILE_LOG':str(log)};trapped=logged|{'ONE_INSTALL_FORBID_COMPILE':'1'}
for args in [['cargo','build'],['rustc','--crate-name','positive_control']]:assert run(args,env=trapped,ok=False).returncode==91
log.write_text('')
with Cluster() as cluster:
 t=start(logged);pid=t.p.pid
 try:
  t.send('let held=42;');notice,_,_=dep(t,'polars',decline=True);assert setup['rev'] in notice and 'acquired' in notice
  assert not Path(E['XDG_STATE_HOME']).exists() and not Path(E['RNX_PROJECT_CACHE']).exists() and not Path(E['XDG_DATA_HOME']).exists();assert '42' in t.send('held')
  t.send('let history_marker=93817;');notice,out,seconds=dep(t,'polars',pid=pid);command,manifest=reopen(out);first=identity(pid)
  assert 'No local variable' in t.send('held');assert str(cwd) in t.send('fs::cwd().unwrap()');shown=frame(t,'first')
  # History is retained, but not evaluated in the replacement.
  assert ':dep polars' in Path(E['RNX_HISTORY']).read_text() and 'history_marker=93817' in Path(E['RNX_HISTORY']).read_text()
  assert 'No local variable' in t.send('history_marker')
  assert 'already installed; session unchanged' in t.send(':dep polars')
  rows['first']={**first,'manifest':str(manifest),'reopen':command,'seconds':seconds,'decline_wrote_nothing':True,'empty_git_cache_before':True,'frame':shown,'same_pid':pid};save_rows()
  t.send('let held=42;');notice,out,seconds=dep(t,'polars postgres',offline=True,pid=pid);assert 'Adding: postgres' in notice and 'Already declared: polars' in notice
  combined=identity(pid);assert 'Reopen this scratch session:' not in out;assert 'No local variable' in t.send('held');frame(t,'combined')
  payload="quote ' ; \\ 🦀";expr='let answer=postgres::query('+json.dumps(cluster.url)+', "SELECT $1::text AS value, $2::int8 AS n", ['+json.dumps(payload,ensure_ascii=False)+',42], #{}).await.unwrap();'
  assert 'error at input' not in t.send(expr);assert 'error' not in t.send('assert!(answer.rows[0].value=='+json.dumps(payload,ensure_ascii=False)+' && answer.rows[0].n==42);').lower()
  assert 'already installed; session unchanged' in t.send(':dep postgres')
  # Interrupt cancels the current input, preserves earlier bindings, then reset clears them.
  os.write(t.master,b'time::sleep(10000).await;\n');time.sleep(.2);os.write(t.master,b'\x03');t.read(timeout=10);assert '5 rows' in t.send('println!("{}",frame.preview().unwrap());')
  assert '[1] >' in t.send(':reset');assert 'No local variable' in t.send('frame');assert 'true' in t.send('polars::lit(1).is_ok()')
  rows['combined']={**combined,'manifest':str(manifest),'reopen':command,'seconds':seconds,'typed_query':True,'reset_interrupt':True};close(t,'first');cluster.wait_idle();rows['postmaster']=cluster.postmaster;save_rows()
 except BaseException:cleanup(t,'first-failed');raise
assert not Path(E['XDG_DATA_HOME']).exists()
(OUT/'cold-compilation.jsonl').write_bytes(log.read_bytes());assert log.read_bytes();log.write_text('')
# A traced second stock session has no network and cannot compile. It also proves
# ordinary source selection never consults the runtime installation store.
trace=OUT/'second.trace';args=['bwrap','--unshare-user','--uid',str(os.getuid()),'--gid',str(os.getgid()),'--unshare-net','--bind','/','/','--dev','/dev','--proc','/proc','--','strace','-f','-qq','-o',trace,'-e','trace=file,connect',exe,'--no-splash','--color=never']
t=start(trapped,args)
try:
 todo=[t.p.pid];matches=[]
 while todo:
  p=todo.pop()
  try:
   if Path('/proc',str(p),'exe').resolve()==exe:matches.append(p)
   todo+=list(map(int,Path('/proc',str(p),'task',str(p),'children').read_text().split()))
  except FileNotFoundError:pass
 assert len(matches)==1;pid=matches[0];_,out,seconds=dep(t,'polars',offline=True,pid=pid);assert identity(pid)==first and not log.read_text();assert 'true' in t.send('polars::lit(1).is_ok()');close(t,'second',eof=True)
 rows['second']={'seconds':seconds,'same_assembly':True,'compile_trapped':True,'network_disabled':True,'EOF':True};save_rows()
except BaseException:cleanup(t,'second-failed');raise
text=trace.read_text();store=str(Path(E['XDG_DATA_HOME'])/'rnx/runtimes');assert store not in text and 'installation.json' not in text and 'current.json' not in text;assert 'AF_INET' not in text;assert not Path(E['XDG_DATA_HOME']).exists()
r=subprocess.run(['/bin/sh','-c',command],input='polars::lit(1).is_ok()\n:q\n',text=True,capture_output=True,env=trapped,cwd=cwd,timeout=30)
assert r.returncode==0 and 'true' in r.stdout and not log.read_text();(OUT/'reopen.log').write_text(r.stdout+r.stderr)
rows['no_runtime_store']={'created':False,'consulted':False,'trace_sha256':sha(trace)};rows['cleanup']={'pids':pids,'postmaster':rows['postmaster'],'all_reaped':all(not Path('/proc',str(p)).exists() for p in pids+[rows['postmaster']])};assert rows['cleanup']['all_reaped'];save_rows();print(kind,'Git journeys passed',flush=True)

import gzip
trace.with_suffix(".trace.gz").write_bytes(gzip.compress(trace.read_bytes(),mtime=0));trace.unlink()
