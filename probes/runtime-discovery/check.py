"""0064 gate 3: product discovery, revalidation and old-session ownership."""
from pathlib import Path
import os,sys,json,subprocess as sp,socket,struct,shutil,hashlib,importlib.util,threading,time,select
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent; B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/runtime-discovery-0064'
assert not W.exists(),'remove only this fixture target before rerunning'
W.mkdir();O.mkdir(exist_ok=True);T=W/'rnx-project';shutil.copy2(R/'tools/project/target/debug/rnx-project',T);S=R/'target/debug/rnx'
E={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','GIT_','CARGO_','RUST'))}
E.update(XDG_DATA_HOME=str(W/'data'),XDG_STATE_HOME=str(W/'state'),RNX_PROJECT_CACHE=str(W/'cache'),RNX_PROJECT_TOOL=str(T),RNX_CONFIG=str(W/'absent-config'),RNX_HISTORY=str(W/'history'),TERM='xterm-256color',PYTHONDONTWRITEBYTECODE='1')
STORE=W/'data/rnx/runtimes';rows=[]
def record(name,**kw): rows.append(dict(name=name,**kw));(O/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS',name,flush=True)
def call(args,env=E,ok=True):
 p=sp.run(list(map(str,args)),env=env,capture_output=True,text=True,timeout=60)
 assert (p.returncode==0)==ok,(args,p.stdout,p.stderr)
 return p
def fixture(name):
 p=W/name;(p/'src').mkdir(parents=True);(p/'Cargo.toml').write_text('[package]\nname="rnx"\nversion="0.0.0"\nedition="2024"\n[workspace]\n');(p/'src/main.rs').write_text('fn main() {}\n');(p/'src/lib.rs').write_text('// '+name+'\n')
 for a in ['polars','postgres']:
  d=p/'adapters'/a;(d/'src').mkdir(parents=True);(d/'src/lib.rs').write_text('// adapter\n');(d/'Cargo.toml').write_text(f'[package]\nname="rnx-{a}"\nversion="0.0.0"\n[workspace]\n[dependencies]\nrnx={{path="../.."}}\n')
 call(['git','init','-q',p]);call(['git','-C',p,'add','.']);call(['git','-C',p,'-c','user.name=Fixture','-c','user.email=f@invalid','-c','commit.gpgsign=false','commit','-qm','snapshot']);return p
def install(p):return call([T,'runtime','install','--from',p]).stdout.split('runtime ',1)[1].splitlines()[0]
def choose(i):call([T,'runtime','select',i])
def tree(p):return {str(q.relative_to(p)):(hashlib.sha256(q.read_bytes()).hexdigest(),q.stat().st_ino,q.stat().st_mtime_ns) for q in p.rglob('*') if q.is_file()}
def frame(k,f):
 b=bytes([1,k])+b''.join(bytes([key])+struct.pack('!I',len(v.encode()))+v.encode() for key,v in sorted(f.items()));return struct.pack('!I',len(b))+b
def exact(s,n):
 b=b''
 while len(b)<n:
  c=s.recv(n-len(b));assert c,'truncated';b+=c
 return b
def receive(s):
 n=struct.unpack('!I',exact(s,4))[0];assert 2<=n<=65536;b=exact(s,n);assert b[0]==1;i=2;f={}
 while i<len(b):
  tag=b[i];n=struct.unpack('!I',b[i+1:i+5])[0];i+=5;f[tag]=b[i:i+n].decode();i+=n
 return b[1],f
def start(env=E):
 a,b=socket.socketpair();a.settimeout(30);p=sp.Popen([T],env=dict(env,RNX_INTERNAL_DEP_FD=str(b.fileno())),pass_fds=(b.fileno(),),stdin=sp.DEVNULL,stdout=sp.PIPE,stderr=sp.PIPE);b.close();a.sendall(frame(1,{1:'polars',2:'',3:str(S),4:'',5:'offline'}));return p,a,receive(a)
def end(p,s):
 s.close();out,err=p.communicate(timeout=10);assert p.returncode==0,(out,err)
def describe(env=E):
 p,s,r=start(env)
 if r[0]==2:s.sendall(frame(3,{}));s.shutdown(socket.SHUT_WR)
 end(p,s);return r
def prepare(env=E,change=lambda:None):
 p,s,(k,d)=start(env);assert k==2,d;change();s.sendall(frame(4,{1:d[1]}));s.shutdown(socket.SHUT_WR);r=receive(s);end(p,s);return d,r
help='rnx-project runtime install --from /path/to/rnx'
for args,needle in [(['runtime','show'],'no runtime is installed'),(['runtime','select','0'*64],'unknown installation ID')]:
 out=call([T,*args],ok=False).stderr;assert needle in out
 if args[1]=='show':assert help in out
assert describe()[0]==8 and help in describe()[1][1] and not STORE.exists();record('absent store and F2 actionable errors, no discovery mutation')
A=fixture('source-a');aid=install(A);Z=fixture('source-b');(Z/'src/lib.rs').write_text('// dirty\n');bid=install(Z);choose(aid);entry=STORE/'entries'/aid;source=entry/'source';before=tree(STORE)
k,d=describe();assert k==2 and aid in d[2] and str(A) in d[2] and 'clean tracked snapshot' in d[2] and str(source) in d[2];assert tree(STORE)==before and not (W/'state').exists();record('selected runtime notice and decline are read-only',notice=d[2])
assert 'unknown installation ID' in call([T,'runtime','select','0'*64],ok=False).stderr
choose(bid);k,d=describe();assert bid in d[2] and 'dirty tracked snapshot' in d[2];choose(aid);record('dirty provenance and multiple selections')
for override in [str(W/'missing'),'', 'relative']:
 k,d=describe(dict(E,RNX_DEP_RUNTIME=override));assert k==8 and 'RNX_DEP_RUNTIME' in d[1]
record('invalid overrides refuse despite valid default')
k,d=describe(dict(E,RNX_DEP_RUNTIME=str(A)));assert k==2 and 'Runtime: override '+str(A) in d[2] and 'Runtime: installation' not in d[2];record('valid override takes precedence')
d,(k,e)=prepare(change=lambda:choose(bid));assert k==8 and 'description changed' in e[1] and not (W/'state').exists();choose(aid);record('selection changed across consent refuses before scratch')
# Unpublished complete entry is never a default.
current=STORE/'current.json';raw=current.read_bytes();current.unlink();assert help in describe()[1][1];current.write_bytes(raw);current.chmod(0o600);record('complete unselected entries are not discovered')
q=source/'src/lib.rs';saved=q.read_bytes();q.write_bytes(b'corrupt');d,(k,e)=prepare();assert k==8 and 'source fingerprint differs' in e[1] and not (W/'state').exists();q.write_bytes(saved);record('corrupt source revalidated before scratch',error=e[1])
renamed=entry.with_name(aid+'.hidden');entry.rename(renamed);k,e=describe();assert k==8 and 'missing' in e[1];renamed.rename(entry);record('deleted selected entry refuses')
# Empty PATH only affects Git spawned after describe; all fixture commands absolute.
no_git=dict(E,PATH=str(W/'no-bin'));d,(k,e)=prepare(no_git);assert k==8 and 'install Git if missing' in e[1] and not (W/'state').exists();record('missing Git actionable before scratch',error=e[1])
# Full validation succeeded if the existing author pause/refusal is reached.
d,(k,e)=prepare(dict(E,RNX_PROJECT_FAIL='dep-author'));assert k==8 and 'injected failure' in e[1];m=Path(d[3]);assert str(source) in m.read_text();record('validated source selected in newly created scratch',manifest=m.read_text())
# A cwd project does not select its runtime.
conflict=W/'cwd';conflict.mkdir();(conflict/'rnx.toml').write_text('[runtime]\npath="/not-the-runtime"\n');old=Path.cwd();os.chdir(conflict)
try:k,d=describe();assert k==2 and aid in d[2]
finally:os.chdir(old)
record('conflicting cwd ignored')
# Bounded strict documents and managed path refusals before consent.
for label,payload in [('unknown field',json.dumps(dict(format=1,id=aid,extra=True)).encode()),('wrong version',json.dumps(dict(format=2,id=aid)).encode()),('oversized',b' '*65537)]:
 current.write_bytes(payload);assert describe()[0]==8;current.write_bytes(raw);record('current document '+label)
for label,path in [('entry',entry),('source',source)]:
 backup=path.with_name(path.name+'.saved');path.rename(backup);path.symlink_to(backup,target_is_directory=True)
 assert describe()[0]==8;path.unlink();backup.rename(path);record('managed symlink '+label)
# A describe which succeeds must not need Git.
k,d=describe(no_git);assert k==2;record('describe needs no Git')
# Real stock pending HTTP operations, no adapter/association shortcut.
spec=importlib.util.spec_from_file_location('term',B/'probes/project-interactive/common.py');term=importlib.util.module_from_spec(spec);spec.loader.exec_module(term)
def until(t,needle):
 end=time.monotonic()+15;out=''
 while time.monotonic()<end:
  if select.select([t.master],[],[],.1)[0]:
   b=os.read(t.master,65536);t.log+=b;out+=term.text(b)
   if needle in out:return out
 raise AssertionError(out)
def journey(label,mutate=lambda:None,restore=lambda:None,env=E,consent=True,decline=False):
 listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();accepted=threading.Event();release=threading.Event();closed=threading.Event();errors=[]
 def server():
  try:
   listener.settimeout(15);conn,_=listener.accept()
   with conn:
    conn.settimeout(15);data=b''
    while b'\r\n\r\n' not in data:data+=conn.recv(4096)
    accepted.set();assert release.wait(30);conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n73')
  except BaseException as e:errors.append(repr(e))
  finally:closed.set()
 th=threading.Thread(target=server);th.start();t=term.Terminal([S,'--no-splash','--color=never'],conflict,env)
 try:
  t.read();t.send(f'let held = 42; let q = http::get("http://127.0.0.1:{listener.getsockname()[1]}/");');t.send('let timer = time::sleep(20); select { _ = q => (), _ = timer => () };');assert accepted.wait(5)
  os.write(t.master,b':dep --offline polars\n')
  if consent:
   until(t,'Continue? [y/N]');mutate();os.write(t.master,b'n\n' if decline else b'y\n')
  else:mutate()
  out=t.read(timeout=30);assert ('refused' in out or decline),out;assert not closed.is_set();assert '42' in t.send('held');release.set();out=t.send('q.await');assert '73' in out,out;os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
  (O/(label+'.pty')).write_bytes(t.log);record(label,pending_request_returned_original_value=True)
 finally:restore();release.set();t.close();th.join(10);listener.close()
 assert not th.is_alive() and not errors,errors
journey('pending survives selection change',lambda:choose(bid),lambda:choose(aid))
journey('pending survives corrupt source',lambda:q.write_bytes(b'corrupt'),lambda:q.write_bytes(saved))
journey('pending survives deleted entry',lambda:entry.rename(renamed),lambda:renamed.rename(entry))
journey('pending survives missing Git',env=no_git)
journey('pending survives invalid override',env=dict(E,RNX_DEP_RUNTIME=str(W/'missing')),consent=False)
journey('pending survives decline',decline=True)
record('matrix complete',groups=len(rows))
