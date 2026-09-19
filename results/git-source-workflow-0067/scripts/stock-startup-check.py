"""Gate 3: actual startup failures, old-owner preservation and same-PID handover."""
from pathlib import Path
import os,sys,json,socket,struct,subprocess,time,signal,importlib.util,select,re
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=Path('/home/me/work/rnx-bench/probes/git-source-workflow/target/stock-startup');O=B/'results/git-source-workflow-0067/stock-startup';O.mkdir(exist_ok=True)
T=Path('/home/me/work/rnx-bench/probes/git-source-workflow/target/rnx');M=W/'project/rnx.toml';P=M.parent
ENV=json.loads((W/'env.json').read_text());ENV.update(STARTUP_EVENTS=str(W/'startup-events'),RNX_PROBE_EVENTS=str(W/'context-events'),RNX_PROBE_RELEASE=str(W/'release'),PYTHONDONTWRITEBYTECODE='1')
BASE={p:p.read_bytes() for p in [M,P/'rnx.lock',P/'rnx.Cargo.lock',P/'.rnx/receipt.json']}
def restore():
 for p,b in BASE.items():p.write_bytes(b)
def call(args,env=ENV,stdin=None):return subprocess.run(list(map(str,args)),env=env,input=stdin,capture_output=True,text=True,timeout=240)
def tool(*args):
 p=call([T,'project',*args,'--manifest',M]);assert p.returncode==0,(p.stdout,p.stderr);return p
# Prebuild through real commands, so per-case preparation attaches without compiling.
tool('add','polars');tool('lock','--offline');tool('build','--offline')
r=json.loads((P/'.rnx/receipt.json').read_text());APP=W/'cache/entries'/r['assembly_key']/'artifacts'/r['executable_blake3']
restore()
spec=importlib.util.spec_from_file_location('term',B/'probes/project-interactive/common.py');term=importlib.util.module_from_spec(spec);spec.loader.exec_module(term)
rows={}
def frame(kind,fields):
 b=bytes([1,kind])+b''.join(bytes([k])+struct.pack('!I',len(v.encode()))+v.encode() for k,v in sorted(fields.items()));return struct.pack('!I',len(b))+b
READY=frame(6,{1:'42'})
def probe(env=ENV):
 a,b=socket.socketpair();a.settimeout(7)
 p=subprocess.Popen([APP,'--no-splash','--color=never','repl'],env=dict(env,RNX_INTERNAL_STARTUP_FD=str(b.fileno())),pass_fds=(b.fileno(),),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE);b.close()
 try:
  out,err=p.communicate(timeout=7);data=b''
  while True:
   c=a.recv(65536)
   if not c:break
   data+=c
  return p.returncode,out,err,data
 finally:
  if p.poll() is None:p.kill();p.wait()
  a.close()
# Version succeeds without running even the builder that rejects real startup.
events=W/'version-events';events.unlink(missing_ok=True)
p=call([APP,'version'],dict(ENV,STARTUP_MODE='error',STARTUP_EVENTS=str(events)));assert p.returncode==0 and not events.exists()
status,out,err,data=probe(dict(ENV,STARTUP_MODE='error',STARTUP_EVENTS=str(events)));assert status!=0 and data!=READY
rows['version_only_does_not_prove_startup']=True
config=W/'probe-config.rn';config.write_text('#{splash:false, color:"never", selected_config_marker:true}\n')
history=W/'probe-history';history.write_text('never_replayed()\n');before=history.read_bytes()
status,out,err,data=probe(dict(ENV,RNX_CONFIG=str(config),RNX_HISTORY=str(history),STARTUP_MODE='seal'))
assert (status,data)==(0,READY),(status,out,err,data)
assert err.count(b'selected_config_marker')==1 and history.read_bytes()==before and b'[1]' not in out
assert 'sealed descriptor' in Path(ENV['STARTUP_EVENTS']).read_text()
rows['session_settings_no_history_no_prompt_and_sealed_probe_descriptor']=True
config.write_text('this is invalid Rune !\n');status,out,err,data=probe(dict(ENV,RNX_CONFIG=str(config)));assert status==0 and data==READY and b'cannot compile config' in err,(status,out,err,data)
rows['invalid_settings_warn_and_fall_back']=True
status,out,err,data=probe(dict(ENV,RNX_MEMORY_CEILING='1'));assert status!=0 and data!=READY and b'ceiling' in err
rows['session_memory_ceiling']=True
# An application entry and source map are never inputs to the private eval.
entry=P/'main.rn';original=entry.read_bytes();entry.write_text('this entry must never compile !!!')
status,out,err,data=probe();assert status==0 and data==READY;entry.write_bytes(original)
rows['application_entry_not_evaluated']=True
def until(t,needle,timeout=30):
 end=time.monotonic()+timeout;out=''
 while time.monotonic()<end:
  if select.select([t.master],[],[],.1)[0]:
   b=os.read(t.master,65536);t.log+=b;out+=term.text(b)
   if needle in out:return out
 raise AssertionError(('missing',needle,out))
def own_events(path,pid):return [s for s in path.read_text().splitlines() if s.startswith(str(pid)+' ')]
def journey(mode,success=False):
 events=W/(mode+'-contexts');events.unlink(missing_ok=True);builds=W/(mode+'-builders');builds.unlink(missing_ok=True);release=W/(mode+'-release');release.unlink(missing_ok=True)
 env=dict(ENV,STARTUP_MODE=mode,STARTUP_EVENTS=str(builds),RNX_PROBE_EVENTS=str(events),RNX_PROBE_RELEASE=str(release))
 history=W/(mode+'-history');env['RNX_HISTORY']=str(history)
 t=term.Terminal([T,'project','session','--manifest',M,'--no-splash','--color=never'],P,env)
 try:
  t.read();pid=t.p.pid;t.send('let held = 42; let value = fixture::value(); let q = fixture::pending(false);');t.send('let timer = time::sleep(5); select { _ = q => (), _ = timer => () };');before=own_events(events,pid);assert any('operation polled' in l for l in before)
  os.write(t.master,b':dep --offline polars\n');notice=until(t,'Continue? [y/N]');assert 'Adding: polars' in notice and 'Already declared: (none)' in notice
  start=time.monotonic();os.write(t.master,b'y\n');phase='';probe_start=None
  if mode=='block':phase=until(t,'dependency phase: startup check',30);probe_start=time.monotonic()
  out=phase+t.read(timeout=30);elapsed=time.monotonic()-start;probe_seconds=None if probe_start is None else time.monotonic()-probe_start
  settled=own_events(events,pid)
  if success:
   assert 'restart is beginning' in out and '[1] >' in out and t.p.pid==pid,(mode,out)
   current=own_events(events,pid);assert any('operation dropped' in l for l in current) and any('value dropped' in l for l in current)
   assert len([l for l in current if 'fixture builder' in l])==2,current
   rebuilt=max(i for i,l in enumerate(current) if 'fixture builder' in l)
   assert all(next(i for i,l in enumerate(current) if name in l)<rebuilt for name in ['operation dropped','value dropped','context dropped'])
   assert '73' in t.send('polars::answer()');missing=t.send('held');assert 'held' in missing and 'error' in missing.lower(),missing
   assert ':dep --offline polars' in history.read_text()
   # A fresh association names the new roster, so a repeated request is a no-op.
   out=t.send(':dep polars');assert 'already installed; session unchanged' in out and 'Continue?' not in out
   calls=builds.read_text().splitlines();assert len(calls)==2 and calls[0].endswith('probe builder') and calls[1]==f'{pid} session builder',calls
   probe_pid=int(calls[0].split()[0]);assert not Path('/proc',str(probe_pid)).exists()
   assert any('context dropped' in l for l in own_events(events,probe_pid))
  else:
   assert 'dependency preparation refused: startup check:' in out,(mode,out)
   assert 'restart is beginning' not in out
   assert own_events(events,pid)==before,(mode,own_events(events,pid),before)
   assert '42' in t.send('held');release.touch();assert '73' in t.send('q.await')
   calls=builds.read_text().splitlines();assert len(calls)==1 and calls[0].endswith('probe builder'),calls
   probe_pid=int(calls[0].split()[0]);assert not Path('/proc',str(probe_pid)).exists()
   if mode=='block':assert 4.8<=probe_seconds<6.5,probe_seconds
   if mode=='flood':assert elapsed<8 and len(t.log)<250000
  os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
  rows[mode]={'seconds_after_consent':elapsed,'builders':calls,'same_pid':t.p.pid==pid,'success':success,'before_consent':before,'at_settlement':settled,'after_quit':own_events(events,pid),'startup_phase_seconds':probe_seconds}
 finally:
  (O/(mode+'.pty')).write_bytes(t.log);t.close();restore()
for mode in ['error','panic','abort','block','flood','spoof','malformed','truncated','cleanup']:journey(mode)
journey('healthy',True)
# F3 mixed-request notice is authored by the tool, not the REPL.
tool('add','polars');tool('lock','--offline');tool('build','--offline')
t=term.Terminal([T,'project','session','--manifest',M,'--no-splash','--color=never'],P,ENV)
try:
 t.read();os.write(t.master,b':dep polars postgres\n');out=until(t,'Continue? [y/N]');assert 'Adding: postgres' in out and 'Already declared: polars' in out and '100 seconds' not in out
 os.write(t.master,b'n\n');t.read();os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
finally:(O/'mixed-notice.pty').write_bytes(t.log);t.close();restore()
rows['mixed_notice_F3']=True
state=W/'notice-state'
assert not state.exists(), 'remove target/notice-state before rerun'
t=term.Terminal([W/'stock-rnx','--no-splash','--color=never'],P,dict(ENV,RNX_DEP_RUNTIME=str(W/'native'),XDG_STATE_HOME=str(state)))
try:
 t.read();os.write(t.master,b':dep polars\n');out=until(t,'Continue? [y/N]');assert 'New scratch project:' in out and 'Adding: polars' in out and 'Already declared: (none)' in out
 os.write(t.master,b'n\n');t.read();assert not state.exists();os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
finally:(O/'scratch-notice.pty').write_bytes(t.log);t.close()
rows['scratch_notice_F3_decline_creates_nothing']=True
(O/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n')
(O/'artifact.json').write_text(json.dumps({'artifact':str(APP),'receipt':r},indent=2)+'\n')
print('PASS',len(rows),'startup groups')
