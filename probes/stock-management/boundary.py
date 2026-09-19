"""Product command boundary, real terminal preservation and quoted recovery."""
from pathlib import Path
import os,sys,json,subprocess as sp,importlib.util,socket,struct,threading,select,time,shutil
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/stock-management-0067';R=B.parent/'rnx'
NEW=W/'rnx';OLD=W/'baseline/target/debug/rnx';CLEAN=W/'clean-rnx'
D=W/'boundary';D.mkdir(exist_ok=True)
E={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','CARGO_','RUST','GIT_'))};E.update(TERM='xterm-256color',RNX_CONFIG=str(D/'absent'),RNX_HISTORY=str(D/'history'),XDG_DATA_HOME=str(D/'data'),XDG_STATE_HOME=str(D/'state'),RNX_PROJECT_CACHE=str(D/'cache'))
def call(exe,args=(),env=E,stdin=None):return sp.run([str(exe),*map(str,args)],cwd=D,env=env,input=stdin,stdout=sp.PIPE,stderr=sp.PIPE,timeout=60)
coordinates_only='--coordinates-only' in sys.argv
rows=json.loads((O/'boundary.json').read_text()) if coordinates_only else {}
cases=[['version'],['--version'],['help'],['eval','42'],['eval','"café"'],['eval','env::vars()?'],['eval','struct A; A.nope()'],['--color=never','eval','1 + 2'],['run','--budget','0','missing'],['--bad'],['session'],['--no-splash','--color=never','repl']]
for name in ['project','runtime','cache']:
 (D/name).write_text('pub fn main(args) { args }\n');cases.append(['run',name,'--verify','two words'])
for i,args in enumerate([] if coordinates_only else cases):
 env={'PATH':E['PATH'],'A':'1','E':''} if args==['eval','env::vars()?'] else E
 a=call(OLD,args,env,b'let n = 9;\nn\n:q\n');b=call(NEW,args,env,b'let n = 9;\nn\n:q\n')
 assert (a.returncode,a.stdout,a.stderr)==(b.returncode,b.stdout,b.stderr),(args,a.stdout,a.stderr,b.stdout,b.stderr)
 rows['ordinary-'+str(i)]={'arguments':args,'status':b.returncode,'stdout':b.stdout.decode(),'stderr':b.stderr.decode()}
for exe in ([NEW] if coordinates_only else [OLD,NEW]):
 p=call(exe,['selfcheck']);assert p.returncode==0 and not p.stderr;rows['selfcheck-'+str(exe)]={'status':0,'byte_comparison':False,'reason':'selfcheck prints its measured elapsed time'}
# Management never enters the runner, with explicit positive control.
config=D/'config';config.write_text('not valid Rune !!!');report=D/'read-report';env=dict(E,RNX_CONFIG=str(config),RNX_TEST_CONFIG_READS=str(report))
for args in [['project','adapters'],['project','help'],['project','unknown'],['runtime','show'],['cache','list'],['management-version']]:
 report.unlink(missing_ok=True);p=call(NEW,args,env);assert not report.exists() and b'cannot compile config' not in p.stderr,(args,p.stderr)
 rows['management-'+','.join(args)]={'status':p.returncode,'runner_entered':False}
p=call(NEW,['--no-splash','repl'],env,b':q\n');assert report.read_text()=='1' and b'cannot compile config' in p.stderr
rows['settings-positive-control']=True

def frame(k,f):
 b=bytes([1,k])+b''.join(bytes([key])+struct.pack('!I',len(v.encode()))+v.encode() for key,v in sorted(f.items()));return struct.pack('!I',len(b))+b
def recv(s):
 def exact(n):
  b=b''
  while len(b)<n:
   c=s.recv(n-len(b));assert c;b+=c
  return b
 n=struct.unpack('!I',exact(4))[0];b=exact(n);assert b[0]==1;i=2;f={}
 while i<len(b):
  k=b[i];n=struct.unpack('!I',b[i+1:i+5])[0];i+=5;f[k]=b[i:i+n].decode();i+=n
 return b[1],f
for exe in [NEW,W/'rnx-project']:
 report.unlink(missing_ok=True);a,b=socket.socketpair();a.settimeout(6)
 p=sp.Popen([str(exe),'management-version'],env=dict(env,RNX_INTERNAL_DEP_FD=str(b.fileno())),pass_fds=[b.fileno()],stdin=sp.DEVNULL,stdout=sp.PIPE,stderr=sp.PIPE);b.close();a.sendall(frame(6,{}));a.shutdown(socket.SHUT_WR);assert recv(a)==(6,{1:'1'});assert a.recv(1)==b'';out,err=p.communicate(timeout=6);assert p.returncode==0 and not out and not err and not report.exists();a.close()
 rows['capability-'+exe.name]=True

spec=importlib.util.spec_from_file_location('terminal',B/'probes/project-interactive/common.py');term=importlib.util.module_from_spec(spec);spec.loader.exec_module(term)
def until(t,needle):
 out='';end=time.monotonic()+12
 while time.monotonic()<end:
  if select.select([t.master],[],[],.1)[0]:
   b=os.read(t.master,65536);t.log+=b;out+=term.text(b)
   if needle in out:return out
 raise AssertionError((needle,out))
# An actual started HTTP future survives both refusal and decline. No fake helper.
for label,exe,consent in [('dirty',W/'dirty-rnx',None),('clean-decline',CLEAN,False),('clean-staged-refusal',CLEAN,True)]:
 d=D/label;d.mkdir(exist_ok=True);traps=d/'traps';traps.mkdir(exist_ok=True)
 for name in ['git','cargo','rustc']:
  f=traps/name;f.write_text('#!/bin/sh\nprintf touched >> '+str(d/'fetch-trap')+'\nexit 91\n');f.chmod(0o755)
 # Stale selection is intentionally corrupt: stock must not consult it.
 store=d/'data/rnx/runtimes';store.mkdir(parents=True);(store/'current.json').write_text('not json')
 env=dict(E,PATH=str(traps),RNX_PROJECT_TOOL=str(d/'missing-explicit-tool'),XDG_DATA_HOME=str(d/'data'),XDG_STATE_HOME=str(d/'state'),RNX_PROJECT_CACHE=str(d/'cache'),RNX_HISTORY=str(d/'history'))
 server=socket.socket();server.bind(('127.0.0.1',0));server.listen();server.settimeout(15);started=threading.Event();release=threading.Event();done=[]
 def serve():
  try:
   c,_=server.accept()
   with c:
    c.recv(8192);started.set();assert release.wait(20);c.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n73')
   done.append(True)
  finally:server.close()
 thread=threading.Thread(target=serve);thread.start();t=term.Terminal([exe,'--no-splash','--color=never'],D,env)
 try:
  t.read();assert 'error' not in t.send('let held = 42; let h = http::get("http://127.0.0.1:'+str(server.getsockname()[1])+'/hold");').lower()
  t.send('let timer = time::sleep(10); select { _ = h => (), _ = timer => () };');assert started.wait(3)
  os.write(t.master,b':dep polars\n')
  if consent is None:
   out=t.read();assert 'default runtime coordinates refused:' in out and 'dirty' in out,out
  else:
   notice=until(t,'Continue? [y/N]');assert 'not yet confirmed reachable' in notice and 'Runtime: Git' in notice and 'Adding: polars' in notice,notice
   os.write(t.master,b'y\n' if consent else b'n\n');out=t.read()
   if consent:assert '0067 gate 3' in out,out
  assert '42' in t.send('held');release.set();assert '73' in t.send('h.await.unwrap().body')
  assert not (d/'fetch-trap').exists() and not (d/'state').exists() and not (d/'cache').exists()
  assert (store/'current.json').read_text()=='not json'
  os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
  rows[label]={'started_http_completed':True,'binding_retained':True,'fetches':0,'state_created':False,'selected_store_ignored':True}
 finally:
  release.set();thread.join(5);t.close();(O/(label+'.pty')).write_bytes(t.log)
 assert done and not thread.is_alive()
(O/'boundary.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS',len(rows),'boundary groups')
