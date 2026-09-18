"""Real rnx serving/association with tiny adapter bodies; engine journeys are gate 4."""
from pathlib import Path
import os,sys,subprocess as sp,json,shutil,socket,struct,re,hashlib
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=Path('/home/me/work/rnx-bench/probes/inventory-final/target/discovery');O=B/'results/inventory-final-0065/discovery';T=W/'rnx-project'
E={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','GIT_','CARGO_','RUST'))};E.update(XDG_DATA_HOME=str(W/'real-data'),XDG_STATE_HOME=str(W/'real-state'),RNX_PROJECT_CACHE=str(W/'real-cache'),RNX_CONFIG=str(W/'absent'),RNX_HISTORY=str(W/'real-history'),RNX_PROJECT_TOOL=str(T))
for log in ['reopen-tool.stdout','reopen-tool.stderr']:
 (O/log).write_text('')
def run(args,**kw):
 p=sp.run(list(map(str,args)),env=E,capture_output=True,text=True,timeout=600,**kw);assert p.returncode==0,(args,p.stdout,p.stderr);return p
src=W/'real-source';src.mkdir()
for name in sp.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0'):
 if name:
  dest=src/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/name,dest)
# Self-contained source closure, replacing only native engines with named functions.
for a in ['polars','postgres']:
 d=src/'adapters'/a;(d/'Cargo.toml').write_text(f'[package]\nname="rnx-{a}"\nversion="0.0.0"\nedition="2024"\n[workspace]\n[dependencies]\nrnx={{path="../..",default-features=false}}\n')
 signature='' if a=='polars' else ', _: rnx::Scope'
 (d/'src/lib.rs').write_text(f'pub fn build(m: &mut rnx::rune::Module{signature}) -> Result<Vec<(String, &\'static str)>, String> {{ m.function("answer", || 73i64).build().map_err(|e| e.to_string())?; Ok(vec![]) }}\n')
 # Explicit auto-discovered old binaries/test files aren't compiled by the wrapper.
run(['git','init','-q',src]);run(['git','-C',src,'add','.'])
p=run([T,'runtime','install','--from',src]);aid=p.stdout.split('runtime ',1)[1].splitlines()[0];store=W/'real-data/rnx/runtimes';installed=store/'entries'/aid/'source'
(src/'plans/discovery-fixture.txt').write_text('second installation\n');run(['git','-C',src,'add','.']);bid=run([T,'runtime','install','--from',src]).stdout.split('runtime ',1)[1].splitlines()[0]
run([T,'runtime','select',aid]);src.rename(W/'real-source-unavailable')
def frame(k,f):
 b=bytes([1,k])+b''.join(bytes([key])+struct.pack('!I',len(v.encode()))+v.encode() for key,v in sorted(f.items()));return struct.pack('!I',len(b))+b
def exact(s,n):
 b=b''
 while len(b)<n:
  c=s.recv(n-len(b));assert c;b+=c
 return b
def receive(s):
 n=struct.unpack('!I',exact(s,4))[0];b=exact(s,n);i=2;f={}
 while i<len(b):
  tag=b[i];n=struct.unpack('!I',b[i+1:i+5])[0];i+=5;f[tag]=b[i:i+n].decode();i+=n
 return b[1],f
def start(req,extra={}):
 a,b=socket.socketpair();a.settimeout(600);p=sp.Popen([T],env=dict(E,**extra,RNX_INTERNAL_DEP_FD=str(b.fileno())),pass_fds=(b.fileno(),),stdin=sp.DEVNULL,stdout=(O/'reopen-tool.stdout').open('a'),stderr=(O/'reopen-tool.stderr').open('a'));b.close();a.sendall(frame(1,req));return p,a,receive(a)
p,s,(k,d)=start({1:'polars',2:'',3:str(R/'target/debug/rnx'),4:'',5:'offline'});assert k==2 and aid in d[2];s.sendall(frame(4,{1:d[1]}));s.shutdown(socket.SHUT_WR);k,ready=receive(s);assert k==5,ready;s.close();assert p.wait(timeout=10)==0
m=Path(d[3]);assert str(installed) in m.read_text();receipt=m.parent/'.rnx/receipt.json';old=receipt.read_bytes()
run([T,'runtime','select',bid]);E['RNX_DEP_RUNTIME']=str(W/'invalid-override')
p=run([T,'session','--manifest',m,'--no-splash','--color=never'],input='polars::answer()\nprintln!("{}", env::var("RNX_INTERNAL_SESSION_V1").unwrap().unwrap());\n:q\n');assert '73' in p.stdout
capsule=re.search(r'\b[0-9a-f]{200,}\b',p.stdout).group();a,b=socket.socketpair();a.sendall(bytes.fromhex(capsule));_,fields=receive(b);a.close();b.close()
p,s,(k,desc)=start({1:'postgres',2:capsule,3:fields[6],4:'polars',5:'offline'});assert k==2,desc;assert 'Adding: postgres' in desc[2] and 'Runtime: override' not in desc[2];s.sendall(frame(3,{}));s.shutdown(socket.SHUT_WR);s.close();assert p.wait(timeout=10)==0
assert receipt.read_bytes()==old and str(installed) in m.read_text()
# Corrupt default metadata also cannot affect an associated session.
current=store/'current.json';raw=current.read_bytes();current.write_text('{}');p=run([T,'eval','--manifest',m,'--','polars::answer()']);assert '73' in p.stdout;current.write_bytes(raw)
(O/'reopen.json').write_text(json.dumps(dict(first_installation=aid,second_installation=bid,scratch=str(m),old_scratch_uses_first=True,associated_ignores_invalid_override_and_default=True,original_path_absent=not src.exists(),receipt_unchanged=True,adapter_bodies='tiny named functions; real rnx library, tool, Cargo and startup probe'),indent=2)+'\n');print('PASS old scratch reopen and associated runtime ownership',flush=True)
