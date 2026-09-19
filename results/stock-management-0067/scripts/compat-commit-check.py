"""Real lifecycle owners around deterministic, test-only commitment stops."""
from pathlib import Path
import os,sys,json,subprocess,time,signal,importlib.util,select,socket,threading
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parents[1];W=Path('/home/me/work/rnx-bench/probes/stock-management/target/compat-commit');O=B/'results/stock-management-0067/compat-commit';O.mkdir(exist_ok=True)
T=W/'rnx-project';M=W/'project/rnx.toml';P=M.parent
ENV=json.loads((W/'env.json').read_text())
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
term=load('term',B/'probes/project-interactive/common.py');Cluster=load('cluster',B/'probes/postgres/cluster.py').Cluster
BASE={p:p.read_bytes() for p in [M,P/'rnx.lock',P/'rnx.Cargo.lock',P/'.rnx/receipt.json']}
def restore():
 for p,b in BASE.items():p.write_bytes(b)
def tool(*args):
 p=subprocess.run(list(map(str,[T,*args,'--manifest',M])),env=ENV,capture_output=True,text=True,timeout=300)
 assert p.returncode==0,(p.stdout,p.stderr)
 return p
# Actual build, then each transition hits that entry. No artifact fabrication.
for args in [('add','polars'),('lock','--offline'),('build','--offline')]:tool(*args)
r=json.loads((P/'.rnx/receipt.json').read_text());APP=W/'cache/entries'/r['assembly_key']/'artifacts'/r['executable_blake3'];restore()
def wait(check,timeout=20):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  v=check()
  if v:return v
  time.sleep(.01)
 raise AssertionError(('condition timeout',timeout))
def until(t,needle):
 out='';end=time.monotonic()+30
 while time.monotonic()<end:
  if select.select([t.master],[],[],.1)[0]:
   b=os.read(t.master,65536);t.log+=b;out+=term.text(b)
   if needle in out:return out
 raise AssertionError((needle,out))
def events(path,pid):return [s for s in path.read_text().splitlines() if s.startswith(str(pid)+' ')]
def sockets(pid):
 result=set()
 for p in Path('/proc',str(pid),'fd').glob('*'):
  try:s=os.readlink(p)
  except FileNotFoundError:continue
  if s.startswith('socket:'):result.add(s)
 return result
class Hold:
 def __init__(self):
  self.server=socket.socket();self.server.bind(('127.0.0.1',0));self.server.listen();self.server.settimeout(.1)
  self.started=threading.Event();self.release=threading.Event();self.closed=threading.Event();self.stop=threading.Event();self.error=None
  self.thread=threading.Thread(target=self.run);self.thread.start()
 def run(self):
  try:
   while not self.stop.is_set():
    try:c,_=self.server.accept();break
    except socket.timeout:continue
   else:return
   with c:
    c.settimeout(.1);b=b''
    while b'\r\n\r\n' not in b:b+=c.recv(4096)
    self.started.set()
    while not self.release.is_set() and not self.stop.is_set():
     try:
      if not c.recv(1):self.closed.set();return
     except socket.timeout:pass
    if self.release.is_set():
     c.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 1\r\nConnection: close\r\n\r\nx')
  except (BrokenPipeError,ConnectionResetError):pass
  except BaseException as e:self.error=str(e)
  finally:self.closed.set()
 def close(self):
  self.stop.set();self.thread.join(3);self.server.close();assert not self.thread.is_alive();assert self.error is None,self.error
rows={}
def case(name,cluster):
 restore();d=W/name;d.mkdir(exist_ok=True)
 for p in d.iterdir():p.unlink()
 ep=d/'events';release=d/'operation-release';marker=d/'marker';go=d/'continue';timeline=d/'timeline';builders=d/'builders'
 point={'post-artifact':'after-cleanup','exec-failure':'before-exec'}.get(name,'before-commit')
 env=dict(ENV,RNX_PROBE_EVENTS=str(ep),RNX_PROBE_RELEASE=str(release),STARTUP_EVENTS=str(builders),RNX_HISTORY=str(d/'history'),RNX_DEP_PAUSE=point,RNX_DEP_MARKER=str(marker),RNX_DEP_RELEASE=str(go),RNX_DEP_TIMELINE=str(timeline))
 if name.startswith('replacement-'):env['REPLACEMENT_MODE']=name.removeprefix('replacement-')
 h=Hold();t=term.Terminal([T,'session','--manifest',M,'--no-splash','--color=never'],P,env);moved=None
 try:
  t.read();pid=t.p.pid;base=sockets(pid)
  out=t.send('let held = 42; let value = fixture::value(); let q = fixture::pending('+str(name=='cleanup-failure').lower()+');')
  assert 'error' not in out.lower(),out
  url=f'http://127.0.0.1:{h.server.getsockname()[1]}/hold'
  # Long enough for full preparation, with an independent per-command server bound.
  out=t.send(f'let h = http::get({json.dumps(url)}); let p = postgres::query({json.dumps(cluster.url)}, "SELECT 1 AS n FROM pg_sleep(12)", [], #{{timeout_ms:15000}});')
  assert 'error' not in out.lower(),out
  for variable in ['q','h']:
   out=t.send(f'let timer = time::sleep(40); select {{ _ = {variable} => (), _ = timer => () }};');assert 'error' not in out.lower(),out
  # Observe request sockets while a final sleep keeps the editor out of readline.
  # Readline itself owns a fresh socketpair at each prompt, unrelated to requests.
  started=d/'started'
  line=f'let timer = time::sleep(40); select {{ _ = p => (), _ = timer => () }}; fs::write_new({json.dumps(str(started))}, "ready").unwrap(); time::sleep(700).await;'
  os.write(t.master,line.encode()+b'\n');wait(started.exists)
  assert h.started.wait(2);activity=wait(cluster.activity);before=events(ep,pid);owned=sockets(pid)-base;assert len(owned)==2,(owned,activity)
  t.read()
  assert any('operation polled' in s for s in before)
  os.write(t.master,b':dep --offline polars\n');notice=until(t,'Continue? [y/N]');assert 'Adding: polars' in notice
  start=time.monotonic_ns();os.write(t.master,b'y\n')
  # Drain Cargo output while awaiting the marker; never poll the old runtime.
  wait_end=time.monotonic()+30
  while not marker.exists():
   if select.select([t.master],[],[],.05)[0]:t.log+=os.read(t.master,65536)
   assert time.monotonic()<wait_end,term.text(t.log)
  assert marker.read_text()==str(APP)
  at_pause=events(ep,pid);pause_sockets=sockets(pid)
  if point=='before-commit':assert before==at_pause and owned<=pause_sockets,(before,at_pause,owned,pause_sockets)
  else:
   assert all(any(x in s for s in at_pause) for x in ['operation dropped','value dropped','context dropped']),at_pause
   assert not (owned & pause_sockets),(owned,pause_sockets)
  if name in ['pre-artifact','post-artifact','exec-failure']:
   moved=APP.with_name(APP.name+'.held');APP.rename(moved)
  if name=='cancel':os.kill(pid,signal.SIGINT)
  else:go.touch()
  pre=name in ['cancel','pre-artifact']
  success=name=='success'
  if pre or success:out=t.read(timeout=30)
  else:out=t.read(False,timeout=30);assert t.p.wait(timeout=5)!=0,(name,out)
  elapsed=(time.monotonic_ns()-start)/1e9
  if moved:moved.rename(APP);moved=None
  settled=events(ep,pid)
  if pre:
   assert 'restart is beginning' not in out and 'dependency preparation refused' in out,(name,out)
   assert settled==before and owned<=sockets(pid),(settled,before,sockets(pid))
   assert '42' in t.send('held');release.touch();assert '73' in t.send('q.await')
   h.release.set();assert '200' in t.send('h.await'),term.text(t.log)
   sql=t.send('assert!(p.await.unwrap().affected == 1);');assert 'error' not in sql.lower(),sql
   os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
  elif success:
   assert 'restart is beginning' in out and '[1] >' in out and t.p.pid==pid,out
   assert not owned&sockets(pid)
   assert '73' in t.send('polars::answer()')
   assert 'error' in t.send('held').lower()
   os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
  else:
   assert 'restart is beginning' in term.text(t.log),(name,out)
   expected={'cleanup-failure':'destructor','post-artifact':'restart failed after cleanup','exec-failure':'exec','replacement-error':'replacement-only','replacement-panic':'panicked'}[name]
   assert expected in out,(expected,out)
   assert not Path('/proc',str(pid)).exists()
  after=events(ep,pid);calls=builders.read_text().splitlines()
  assert calls[0].endswith('probe'),calls
  assert len(calls)==(2 if success or name.startswith('replacement-') else 1),calls
  for line in calls:assert not Path('/proc',line.split()[0]).exists()
  assert all(any(x in s for s in after) for x in ['operation dropped','value dropped','context dropped']),after
  assert h.closed.wait(3)
  backend_start=time.monotonic();cluster.wait_idle(timeout=17)
  rows[name]={'precommit_preserved':pre,'seconds_after_consent':elapsed,'started_activity':activity,'socket_identities':sorted(owned),'pause_sockets':sorted(pause_sockets),'before':before,'at_pause':at_pause,'at_settlement':settled,'after_exit':after,'builders':calls,'backend_residual_after_exit_seconds':time.monotonic()-backend_start,'timeline':timeline.read_text().splitlines(),'status':t.p.returncode}
 finally:
  if moved:moved.rename(APP)
  (O/(name+'.pty')).write_bytes(t.log);t.close();h.close();restore()
 with (O/'matrix.json').open('w') as f:json.dump(rows,f,indent=2)
 print('PASS',name,flush=True)
with Cluster() as cluster:
 for name in ['cancel','pre-artifact','success','cleanup-failure','post-artifact','exec-failure','replacement-error','replacement-panic']:case(name,cluster)
print('PASS',len(rows),'commitment cases; private cluster reaped')
