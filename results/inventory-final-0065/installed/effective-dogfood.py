"""Real :dep Polars/PostgreSQL journeys; no engine or compilation substitutes."""
from pathlib import Path
import os,sys,json,subprocess,importlib.util,time,select,re,shlex,hashlib,tomllib
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parents[1];R=Path('/home/me/work/rnx-bench/probes/inventory-final/target/installed/data/rnx/runtimes/entries/b626021f98283100eede418c15d0936d0328a8253b1df5b5d99c7b6f0ea7d50f/source');W=Path(os.environ.get('RNX_DOGFOOD_TARGET', H/'target'));O=Path(os.environ.get('RNX_DOGFOOD_RESULTS', B/'results/session-dogfood-0063'));O.mkdir(exist_ok=True)
T=W/'bin/rnx-project';S=W/'bin/rnx';ENV=json.loads((W/'env.json').read_text())
assert not (W/'cache/entries').exists(), 'cold control requires a fresh target/cache'
assert not Path(ENV['XDG_STATE_HOME']).exists(), 'fresh private state required'
for name in ['cwd','absolute-project','relative-project','traps']:(W/name).mkdir(exist_ok=True)
CWD=W/'cwd';rows={};pids=[]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
term=load('terminal',B/'probes/project-interactive/common.py');Cluster=load('cluster',B/'probes/postgres/cluster.py').Cluster
def save(): (O/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n')
def call(args,env=ENV,cwd=CWD,timeout=600):
 p=subprocess.run(list(map(str,args)),env=env,cwd=cwd,capture_output=True,text=True,timeout=timeout)
 assert p.returncode==0,(args,p.stdout,p.stderr)
 return p
real_cargo=__import__('shutil').which('cargo');real_rustc=__import__('shutil').which('rustc')
# Commands other than compilation still use the actual Cargo and compiler.
for name,real in [('cargo',real_cargo),('rustc',real_rustc)]:
 trap=W/'traps'/name
 trap.write_text('#!/usr/bin/python3\nimport os,sys,json\na=sys.argv[1:]\ncompile_call=("build" in a or "rustc" in a) if '+repr(name)+'=="cargo" else ("--crate-name" in a and not any(v.startswith("--print") for v in a))\nif compile_call:\n with open(os.environ["COMPILE_LOG"],"a") as f:f.write(json.dumps(["'+name+'",*a])+"\\n")\n if os.environ.get("FORBID_COMPILE")=="1":raise SystemExit(91)\nos.execv('+repr(real)+',['+repr(real)+',*a])\n');trap.chmod(0o755)
TRAP_ENV=dict(ENV,PATH=str(W/'traps')+':'+ENV['PATH'],COMPILE_LOG=str(W/'compile.log'))
trapped=dict(TRAP_ENV,FORBID_COMPILE='1')
# Positive controls prove both traps really reject, without running compilation.
for cmd in [[W/'traps/cargo','build'],[W/'traps/rustc','--crate-name','trap_control']]:
 p=subprocess.run(list(map(str,cmd)),env=trapped,capture_output=True);assert p.returncode==91
(W/'compile.log').write_text('')
def until(t,needle,timeout=30):
 stop=time.monotonic()+timeout;out=''
 while time.monotonic()<stop:
  if select.select([t.master],[],[],.1)[0]:
   b=os.read(t.master,65536);t.log+=b;out+=term.text(b)
   if needle in out:return out
 raise AssertionError(('missing',needle,out))
def terminal(label,args,env=ENV):
 t=term.Terminal(args,CWD,dict(env,RNX_HISTORY=str(W/(label+'-history'))));pids.append(t.p.pid);t.read();return t

def close(t,label):
 try:
  os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
 finally:
  (O/(label+'.pty')).write_bytes(t.log);t.close();t._closed=True
 assert not Path('/proc',str(t.p.pid)).exists()
def finish_failed(t,label):
 if getattr(t,'_closed',False):return
 (O/(label+'.pty')).write_bytes(t.log);t.close();t._closed=True
def dep(t,line,adding,already):
 os.write(t.master,line.encode()+b'\n');notice=until(t,'Continue? [y/N]')
 assert f'Adding: {adding}' in notice and f'Already declared: {already}' in notice,notice
 assert 'bindings and declarations will be lost' in notice
 if "New scratch project:" in notice:
  assert 'Runtime: installation b626021f98283100eede418c15d0936d0328a8253b1df5b5d99c7b6f0ea7d50f at /home/me/work/rnx-bench/probes/inventory-final/target/installed/data/rnx/runtimes/entries/b626021f98283100eede418c15d0936d0328a8253b1df5b5d99c7b6f0ea7d50f/source' in notice
  assert '/home/me/work/rnx-bench/probes/inventory-final/target/installed/original' in notice and '0c056927db1cf3bf7330b0e81218b385b940eee9' in notice
 return notice
def handover(t):
 pid=t.p.pid;start=time.monotonic();os.write(t.master,b'y\n');out='';observed=[];stop=time.monotonic()+600
 while time.monotonic()<stop:
  if select.select([t.master],[],[],.1)[0]:
   chunk=os.read(t.master,65536);t.log+=chunk;out+=term.text(chunk)
   now=time.monotonic()-start
   for label in ['dependency phase: author','dependency phase: resolve','dependency phase: build/attach','dependency phase: startup check','restart is beginning']:
    if label in out and not any(v['label']==label for v in observed):observed.append({'label':label,'seconds':now})
   if re.search(r'\[1\] > \r*$',out):break
 else:raise AssertionError(('handover timeout',out))
 observed.append({'label':'first prompt','seconds':time.monotonic()-start})
 with (O/'phases.jsonl').open('a') as f:f.write(json.dumps({'pid':pid,'observations':observed})+'\n')
 assert 'restart is beginning' in out and '[1] >' in out and t.p.pid==pid,out
 assert os.tcgetpgrp(t.master)==pid
 assert not Path('/proc',str(pid),'task',str(pid),'children').read_text().strip()
 # Output is emitted by the new context, following the commitment announcement.
 return out,time.monotonic()-start
def identity(t):
 exe=Path('/proc',str(t.p.pid),'exe').resolve();assert exe.parent.name=='artifacts';return {'artifact':str(exe),'assembly_key':exe.parent.parent.name,'sha256':hashlib.sha256(exe.read_bytes()).hexdigest()}
def bindings_and_cwd(t):
 out=t.send('held');assert 'No local variable `held`' in out,out
 out=t.send('fs::absolute(".").unwrap()');assert str(CWD) in out,out

def frame_journey(t,prefix):
 lines=[f'fs::write_new("{prefix}.csv", "category,value\\na,1\\na,2\\n🦀,3\\n🦀,4\\nmissing,\\n").unwrap();',
 f'let frame = polars::read_csv("{prefix}.csv", [("category","string"),("value","i64")]).unwrap();',
 'let grouped = frame.lazy().filter(polars::col("value").gt(polars::lit(1).unwrap())).group_by([polars::col("category")]).unwrap();',
 'let plan = grouped.agg([polars::col("value").sum().alias("total")]).unwrap().sort(["category"]).unwrap();',
 'let result = plan.collect().unwrap();']
 for line in lines:
  out=t.send(line);assert 'error at input' not in out,out
 out=t.send('println!("{}", result.preview().unwrap());');assert '"a" | 2' in out and '"🦀" | 7' in out,out
 out=t.send('frame.lazy().sort(["missing"]).unwrap().collect()');assert 'Err' in out and 'missing' in out,out
 out=t.send('println!("{}", frame.preview().unwrap());');assert '5 rows' in out,out
 t.send(f'result.write_parquet_new("{prefix}.parquet").unwrap();')
 out=t.send(f'assert!(polars::read_parquet("{prefix}.parquet").unwrap().preview().unwrap() == result.preview().unwrap());');assert 'error' not in out.lower(),out
 out=t.send('assert!(plan.collect().unwrap().preview().unwrap() == result.preview().unwrap());');assert 'error' not in out.lower(),out
 assert (CWD/(prefix+'.csv')).is_file() and (CWD/(prefix+'.parquet')).is_file()

def recall(t):
 t.send('let history_marker = 93817;')
 # Leave this as the most recent ordinary input before the dependency command.
def recall_after(t):
 # Up-arrow reads the preceding :dep line, then the marker. Ctrl-C discards it.
 os.write(t.master,b'\x1b[A\x1b[A');out=until(t,'history_marker');assert '93817' in out
 os.write(t.master,b'\x03');t.read()
 out=t.send('history_marker');assert 'No local variable' in out,out

# First stock session: decline writes nothing, then a genuine cold target build.
t=terminal('scratch-first',[S,'--no-splash','--color=never'],TRAP_ENV)
try:
 t.send('let held = 42;');notice=dep(t,':dep --offline polars','polars','(none)');assert 'New scratch project:' in notice
 os.write(t.master,b'n\n');t.read();assert not Path(ENV['XDG_STATE_HOME']).exists();assert not (W/'cache').exists()
 assert '42' in t.send('held');recall(t)
 dep(t,':dep --offline polars','polars','(none)');out,seconds=handover(t)
 assert 'Reopen this scratch session:' in out and out.index('restart is beginning')<out.index('Reopen this scratch session:')
 command=out.split('Reopen this scratch session:\r\n  ',1)[1].split('\r\n',1)[0]
 argv=shlex.split(command);assert argv[:2]==[str(T),'session'];manifest=Path(argv[3]);assert manifest.is_file() and "'" in str(manifest)
 first=identity(t);assert (W/'compile.log').read_text();(O/'cold-compile.log').write_text((W/'compile.log').read_text());rows['first_scratch']={**first,'seconds':seconds,'command':command,'manifest':str(manifest),'cold_target':True,'decline_wrote_nothing':True}
 recall_after(t);bindings_and_cwd(t);frame_journey(t,'first')
 out=t.send(':dep polars');assert 'already installed; session unchanged' in out and 'Continue?' not in out
 close(t,'scratch-first');save();print('PASS first scratch, cold build and frame journey',flush=True)
except BaseException:finish_failed(t,'scratch-first');raise
# Second consumer: any attempt to compile fails, and the compile log stays empty.
(W/'compile.log').write_text('');t=terminal('scratch-second',[S,'--no-splash','--color=never'],trapped)
try:
 t.send('let held = 42;');dep(t,':dep --offline polars','polars','(none)');out,seconds=handover(t)
 second=identity(t);assert second==first and not (W/'compile.log').read_text(),out
 bindings_and_cwd(t);assert 'true' in t.send('polars::lit(1).is_ok()');close(t,'scratch-second')
 rows['second_scratch']={**second,'seconds':seconds,'compilation_trapped':True};save();print('PASS second stock attaches without compilation',flush=True)
except BaseException:finish_failed(t,'scratch-second');raise
# Execute the exact printed shell command, including apostrophe quoting.
p=subprocess.run(['/bin/sh','-c',command],input='polars::lit(1).is_ok()\n:q\n',text=True,capture_output=True,env=dict(trapped,RNX_HISTORY=str(W/'reopened-history')),cwd=CWD,timeout=30)
assert p.returncode==0 and 'true' in p.stdout and not (W/'compile.log').read_text(),(p.stdout,p.stderr)
rows['printed_command_reopens']=True;(O/'reopened.txt').write_text(p.stdout+p.stderr);save()
with Cluster() as cluster:
 for kind in ['absolute','relative']:
  project=W/(kind+'-project');runtime=str(R) if kind=='absolute' else os.path.relpath(R,project)
  m=project/'rnx.toml';(project/'main.rn').write_text('this entry is deliberately invalid and must not run')
  m.write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath='+json.dumps(runtime)+'\n')
  for args in [('add','polars'),('lock','--offline'),('build','--offline')]:call([T,*args,'--manifest',m],env=trapped)
  t=terminal(kind,[T,'session','--manifest',m,'--no-splash','--color=never'],TRAP_ENV if kind=='absolute' else trapped)
  try:
   assert identity(t)==first
   t.send('let held = 42;');assert 'true' in t.send('polars::lit(1).is_ok()');recall(t)
   dep(t,':dep --offline polars postgres','postgres','polars');out,seconds=handover(t);assert 'Reopen this scratch session:' not in out
   combined=identity(t)
   if kind=='absolute':combined_first=combined;assert (W/'compile.log').read_text();(O/'compile.log').write_text((W/'compile.log').read_text());(W/'compile.log').write_text('')
   else:assert combined==combined_first and not (W/'compile.log').read_text()
   recall_after(t);bindings_and_cwd(t);frame_journey(t,kind)
   payload="quote ' SQL ; \\ and 🦀";sql='SELECT $1::text AS value, $2::int8 AS n'
   expr='let answer = postgres::query('+json.dumps(cluster.url)+', '+json.dumps(sql)+', ['+json.dumps(payload,ensure_ascii=False)+', 42], #{}).await.unwrap();'
   out=t.send(expr);assert 'error at input' not in out,out
   out=t.send('assert!(answer.rows[0].value == '+json.dumps(payload,ensure_ascii=False)+' && answer.rows[0].n == 42);');assert 'error' not in out.lower(),out
   out=t.send(':dep postgres');assert 'already installed; session unchanged' in out
   doc=tomllib.loads(m.read_text());assert doc['native']['postgres']['hook']=='lifecycle'
   assert Path(doc['native']['postgres']['path']).is_absolute()==(kind=='absolute')
   assert doc['native']['polars']['path']==runtime+'/adapters/polars'
   close(t,kind);cluster.wait_idle()
   rows[kind]={'identity':combined,'seconds':seconds,'typed_query':True,'polars_live':True,'declaration':doc['native'],'no_backend_after_quit':True};save();print('PASS',kind,'mixed project and typed query',flush=True)
  except BaseException:finish_failed(t,kind);raise
 postmaster=cluster.postmaster
assert not Path('/proc',str(postmaster)).exists()
assert all(not Path('/proc',str(pid)).exists() for pid in pids)
rows['cleanup']={'session_pids':pids,'postmaster':postmaster,'all_gone':True};save()
print('PASS gate 4 real journeys',flush=True)
