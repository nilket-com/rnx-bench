"""Unassociated discovery, capability refusals, exact quoted recovery and old peers."""
from pathlib import Path
import os,sys,json,subprocess as sp,importlib.util,shutil,re,socket,struct,select,time
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/stock-management-0067';D=W/'discovery';D.mkdir(exist_ok=True)
P=W/'stock-preparation/project';M=P/'rnx.toml';T=W/'rnx';COMPAT=W/'rnx-project';OLD=W/'baseline/tools/project/target/debug/rnx-project'
E=json.loads((W/'stock-preparation/env.json').read_text());E.update(RNX_PROBE_EVENTS=str(D/'events'),RNX_PROBE_RELEASE=str(D/'release'),RNX_HISTORY=str(D/'history'),RNX_CONFIG=str(D/'missing-config'))
def call(args,env=E,stdin=None):return sp.run(list(map(str,args)),env=env,input=stdin,capture_output=True,text=True,timeout=300)
c=call([T,'project','session','--manifest',M,'--no-splash','--color=never'],stdin='println!("{}", env::var("RNX_INTERNAL_SESSION_V1").unwrap().unwrap());\n:q\n');assert c.returncode==0,(c.stdout,c.stderr)
CAP=re.search(r'\b[0-9a-f]{200,}\b',c.stdout).group()
def frame(k,f):
 b=bytes([1,k])+b''.join(bytes([key])+struct.pack('!I',len(v.encode()))+v.encode() for key,v in sorted(f.items()));return struct.pack('!I',len(b))+b
def decode(b):
 assert int.from_bytes(b[:4],'big')==len(b)-4 and b[4]==1;i=6;f={}
 while i<len(b):
  k=b[i];n=int.from_bytes(b[i+1:i+5],'big');i+=5;f[k]=b[i:i+n].decode();i+=n
 return f
fields=decode(bytes.fromhex(CAP));APP=Path(fields[6]);rows={}
spec=importlib.util.spec_from_file_location('term',B/'probes/project-interactive/common.py');term=importlib.util.module_from_spec(spec);spec.loader.exec_module(term)
path=D/'path';path.mkdir(exist_ok=True);(path/'rnx').unlink(missing_ok=True);(path/'rnx').symlink_to(T)
empty=D/'empty';empty.mkdir(exist_ok=True)
slow=D/'slow';slow.write_text('#!/usr/bin/python3\nimport os,time\nopen('+repr(str(D/'slow-pid'))+',"w").write(str(os.getpid()))\ntime.sleep(60)\n');slow.chmod(0o755)
for label,overrides,expected in [
 ('missing',{'PATH':str(empty),'RNX_PROJECT_TOOL':None},'cannot locate installed rnx'),
 ('invalid-override',{'PATH':str(path),'RNX_PROJECT_TOOL':str(D/'absent')},'No such file or directory'),
 ('relative-override',{'RNX_PROJECT_TOOL':'relative'},'must be absolute'),
 ('not-capable',{'RNX_PROJECT_TOOL':'/bin/true'},'refused'),
 ('old-override',{'RNX_PROJECT_TOOL':str(OLD)},'refused'),
 ('timeout',{'RNX_PROJECT_TOOL':str(slow)},'refused'),
 ('path-stock',{'PATH':str(path),'RNX_PROJECT_TOOL':None},'custom'),
 ('explicit-compat',{'RNX_PROJECT_TOOL':str(COMPAT)},'custom'),
]:
 events=D/(label+'.events');release=D/(label+'.release');events.unlink(missing_ok=True);release.unlink(missing_ok=True);env=dict(E,RNX_INTERNAL_SESSION_V1='',RNX_PROBE_EVENTS=str(events),RNX_PROBE_RELEASE=str(release))
 for key,v in overrides.items():
  if v is None:env.pop(key,None)
  else:env[key]=v
 t=term.Terminal([APP,'--no-splash','--color=never'],D,env)
 try:
  t.read();t.send('let held = 42; let q = fixture::pending(false);');t.send('let timer=time::sleep(5); select { _ = q => (), _ = timer => () };');before=events.read_bytes();assert b'operation polled' in before
  os.write(t.master,b':dep polars\n');out=t.read(timeout=15);assert expected in out,(label,out);assert 'Continue?' not in out and events.read_bytes()==before
  assert '42' in t.send('held');release.touch();assert '73' in t.send('q.await');os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
  rows[label]=dict(old_work_preserved=True,output=out)
 finally:(O/(label+'-discovery.pty')).write_bytes(t.log);t.close()
 if label=='timeout':assert not Path('/proc', (D/'slow-pid').read_text()).exists()
# Obtain an association from the actual accepted old manager, then delegate
# from the current assembled runner. Failure before authoring retains old work.
oldproject=D/'old-project';oldproject.mkdir(exist_ok=True);oldmanifest=oldproject/'rnx.toml'
oldmanifest.write_text(M.read_text().replace('../native',str(W/'stock-preparation/native')));(oldproject/'main.rn').write_text('pub fn main(_) { 42 }\n')
for cmd in ['lock','build']:
 p=call([OLD,cmd,'--offline','--manifest',oldmanifest]);assert p.returncode==0,(p.stdout,p.stderr)
p=call([OLD,'session','--manifest',oldmanifest,'--no-splash','--color=never'],stdin='println!("{}", env::var("RNX_INTERNAL_SESSION_V1").unwrap().unwrap());\n:q\n');assert p.returncode==0,(p.stdout,p.stderr)
oldcap=re.search(r'\b[0-9a-f]{200,}\b',p.stdout).group();assert decode(bytes.fromhex(oldcap))[2]==str(OLD)
events=D/'old-peer.events';release=D/'old-peer.release';events.unlink(missing_ok=True);release.unlink(missing_ok=True)
env=dict(E,RNX_INTERNAL_SESSION_V1=oldcap,RNX_PROJECT_FAIL='dep-author',RNX_PROBE_EVENTS=str(events),RNX_PROBE_RELEASE=str(release))
t=term.Terminal([Path(decode(bytes.fromhex(oldcap))[6]),'--no-splash','--color=never'],D,env)
try:
 t.read();t.send('let q=fixture::pending(false);');t.send('let timer=time::sleep(5); select { _=q=>(), _=timer=>() };');before=events.read_bytes()
 os.write(t.master,b':dep polars\n');out='';end=time.monotonic()+10
 while 'Continue? [y/N]' not in out:
  assert time.monotonic()<end,out
  if select.select([t.master],[],[],.1)[0]:
   chunk=os.read(t.master,65536);t.log+=chunk;out+=term.text(chunk)
 os.write(t.master,b'y\n');out=t.read();assert 'injected failure at dep-author' in out and events.read_bytes()==before,out
 release.touch();assert '73' in t.send('q.await');os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
 rows['old-manager-issued-association']=dict(interoperates=True,injected_failure_retains_started_work=True,output=out)
finally:(O/'old-peer.pty').write_bytes(t.log);t.close()
# Recovery under paths that need shell quoting. Execute the exact emitted lines.
manager=D/"manager's rnx";shutil.copy2(T,manager)
project=D/"project's space";project.mkdir(exist_ok=True);manifest=project/"rnx's.toml"
s=M.read_text().replace('../native',str(W/'stock-preparation/native'));manifest.write_text(s);(project/'main.rn').write_text('pub fn main(_) { 42 }\n')
for cmd in ['lock','build']:
 p=call([manager,'project',cmd,'--offline','--manifest',manifest]);assert p.returncode==0,(p.stdout,p.stderr)
lock=project/'rnx.lock';data=json.loads(lock.read_text());data['format']=2;lock.write_text(json.dumps(data));old=lock.read_bytes()
p=call([manager,'project','eval','--manifest',manifest,'--','42']);assert p.returncode!=0 and lock.read_bytes()==old,p.stderr
lines=[line.strip() for line in p.stderr.splitlines() if " project lock --manifest " in line or " project build --manifest " in line];assert len(lines)==2,p.stderr
# No rnx or rnx-project on PATH. Cargo/Rust/Git remain prerequisites.
private=D/'prerequisites';private.mkdir(exist_ok=True)
for name in ['cargo','rustc','rustdoc','git','cc','gcc','ld','as','ar','ranlib']:
 real=shutil.which(name)
 if real:(private/name).symlink_to(real)
env=dict(E,PATH=str(private))
for line in lines:
 p=call(['/bin/sh','-c',line],env);assert p.returncode==0,(line,p.stdout,p.stderr)
p=call([manager,'project','eval','--manifest',manifest,'--','42'],env);assert p.returncode==0 and p.stdout.strip()=='42',(p.stdout,p.stderr)
rows['quoted-recovery']={'commands':lines,'executed_exactly':True,'manager_on_PATH':False}
(O/'discovery.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS',len(rows),'discovery groups')
