"""Real preparation endpoint and terminal preservation; startup readiness is gate 3."""
from pathlib import Path
import json,os,sys,socket,struct,subprocess,time,signal,importlib.util,re,fcntl,select,hashlib
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=Path('/home/me/work/rnx-bench/probes/removal-final/target/preparation');O=B/'results/removal-final-0066/preparation';O.mkdir(exist_ok=True)
T=R/'tools/project/target/debug/rnx-project';STOCK=W/'stock-rnx';P=W/'project';M=P/'rnx.toml'
ENV=json.loads((W/'env.json').read_text());ENV.update(RNX_PROBE_EVENTS=str(W/'default-events'),RNX_PROBE_RELEASE=str(W/'release'))
spec=importlib.util.spec_from_file_location('terminal',B/'probes/project-interactive/common.py');term=importlib.util.module_from_spec(spec);spec.loader.exec_module(term)
rows={}
def call(args,env=ENV,stdin=None):return subprocess.run(list(map(str,args)),env=env,input=stdin,capture_output=True,text=True,timeout=240)
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
  tag=b[i];n=struct.unpack('!I',b[i+1:i+5])[0];i+=5;assert tag not in f;f[tag]=b[i:i+n].decode();i+=n
 return b[1],f
# The carrier is emitted by the real launch, never reconstructed by the fixture.
c=call([T,'session','--manifest',M,'--no-splash','--color=never'],stdin='println!("{}", env::var("RNX_INTERNAL_SESSION_V1").unwrap().unwrap());\n:q\n');assert c.returncode==0,(c.stdout,c.stderr)
ASSOC=re.search(r'\b[0-9a-f]{200,}\b',c.stdout).group();raw=bytes.fromhex(ASSOC);a,b=socket.socketpair();a.sendall(raw);_,FIELDS=receive(b);a.close();b.close();APP=Path(FIELDS[6]);assert APP.is_file()
BASE={p:p.read_bytes() for p in [M,P/'rnx.lock',P/'rnx.Cargo.lock',P/'.rnx/receipt.json']}
def restore():
 for p,b in BASE.items():p.write_bytes(b)
 (P/'main.rn').write_text('pub fn main(_) { 42 }\n')
def request(names='polars',assoc=ASSOC,exe=APP,installed='fixture'):return {1:names,2:assoc,3:str(exe),4:installed,5:'offline'}
def start(req,env=ENV):
 a,b=socket.socketpair();a.settimeout(30);p=subprocess.Popen([T],env=dict(env,RNX_INTERNAL_DEP_FD=str(b.fileno())),pass_fds=(b.fileno(),),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE);b.close();a.sendall(frame(1,req));return p,a,receive(a)
def end(p,s):
 s.close();o,e=p.communicate(timeout=10);assert p.returncode==0,(o,e);return (o+e).decode()
def decline(req=request(),env=ENV):
 p,s,result=start(req,env)
 if result[0]==2:s.sendall(frame(3,{}));s.shutdown(socket.SHUT_WR)
 end(p,s);return result
assert decline()[0]==2
# Source contents are not active assembly identity. Raw receipt bytes are not either.
(P/'main.rn').write_text('pub fn main(_) { 99 }\n');assert decline()[0]==2;restore()
old=APP.stat();os.utime(APP,ns=(old.st_atime_ns,old.st_mtime_ns+1000000000))
c=call([T,'eval','--manifest',M,'--','42']);assert c.returncode==0,(c.stdout,c.stderr)
assert (P/'.rnx/receipt.json').read_bytes()!=BASE[P/'.rnx/receipt.json'];assert decline()[0]==2
BASE[P/'.rnx/receipt.json']=(P/'.rnx/receipt.json').read_bytes()
rows['source_edit_and_real_stamp_refresh_keep_association']=True
for path,bad in [(P/'rnx.lock',b'{}'),(P/'.rnx/receipt.json',b'{}'),(P/'rnx.Cargo.lock',b'bad')]:
 path.write_bytes(bad);assert decline()[0]==8;restore()
M.write_bytes(BASE[M].replace(b'builder="build"',b'builder="changed"'));assert decline()[0]==8;restore()
for req in [request(installed='other'),request(exe=STOCK),request(assoc=ASSOC+'00'),request(names='polars\npolars'),request(names='unknown')]:assert decline(req)[0]==8
rows['real_lock_receipt_pair_declarations_executable_roster_and_names_refuse']=True
for name in ['polars','postgres']:
 state=W/('describe-'+name);env=dict(ENV,XDG_STATE_HOME=str(state),RNX_DEP_RUNTIME=str(W/'native'))
 k,d=decline(request(name,'',STOCK,''),env);assert k==2 and not state.exists() and ('100 seconds' in d[2])==(name=='polars')
rows['scratch_describe_decline_is_read_only_and_cost_is_specific']=True
for kind in ['symlink','fifo']:
 state=W/('unsafe-'+kind);state.mkdir(exist_ok=True);r=state/'rnx'
 if not r.exists():
  if kind=='fifo':os.mkfifo(r)
  else:r.symlink_to(P,target_is_directory=True)
 assert decline(request('polars','',STOCK,''),dict(ENV,XDG_STATE_HOME=str(state),RNX_DEP_RUNTIME=str(W/'native')))[0]==8
rows['managed_scratch_symlinks_and_fifos_refuse']=True
# Consent revalidation precedes Project::open and any mutation.
p,s,(k,d)=start(request());assert k==2;M.write_bytes(BASE[M]+b'# editor\n');s.sendall(frame(4,{1:d[1]}));s.shutdown(socket.SHUT_WR);k,e=receive(s);assert k==8 and 'description changed' in e[1];end(p,s);restore()
rows['changed_description_needs_new_consent']=True
# Inject real workflow faults; inspect which files were published.
for fault,expected in [('dep-author',False),('before-add-rename',False),('after-add-rename',True),('dep-resolve',True),('after-cargo-publication',True),('after-json-publication',True),('dep-build',True)]:
 p,s,(k,d)=start(request(),dict(ENV,RNX_PROJECT_FAIL=fault));assert k==2;(W/'last-description.json').write_text(json.dumps(d));s.sendall(frame(4,{1:d[1]}));s.shutdown(socket.SHUT_WR);k,e=receive(s);assert k==8 and 'injected failure' in e[1],(fault,k,e);end(p,s);assert (M.read_bytes()!=BASE[M])==expected
 rows['publication_'+fault]={'manifest_changed':expected,'diagnostic':e[1]};restore()
# Normal tool lock gives actual contention, not a fabricated ready document.
f=open(P/'.rnx/command.lock','r+');fcntl.flock(f,fcntl.LOCK_EX)
p,s,(k,d)=start(request());assert k==2;s.sendall(frame(4,{1:d[1]}));s.shutdown(socket.SHUT_WR);k,e=receive(s);assert k==8 and 'another project command' in e[1];end(p,s);f.close()
rows['project_contention_refuses_before_authoring']=True
# PTY: output through consent, then recover and observe before another input.
def until(t,needle,timeout=15):
 out='';stop=time.monotonic()+timeout
 while time.monotonic()<stop:
  if select.select([t.master],[],[],.1)[0]:
   b=os.read(t.master,65536);t.log+=b;out+=term.text(b)
   if needle in out:return out
 raise AssertionError(('missing',needle,out))
def journey(label,env_changes=None,dep=':dep --offline polars',consent=True,cancel=False,assoc=ASSOC,exe=APP,expected='refused'):
 events=W/(label+'.events');events.unlink(missing_ok=True);release=W/(label+'.release');release.unlink(missing_ok=True)
 env=dict(ENV,RNX_INTERNAL_SESSION_V1=assoc,RNX_PROBE_EVENTS=str(events),RNX_PROBE_RELEASE=str(release));env.update(env_changes or {})
 t=term.Terminal([exe,'--no-splash','--color=never'],P,env)
 try:
  t.read();t.send('let held = 42; let q = fixture::pending(false);');t.send('let timer = time::sleep(5); select { _ = q => (), _ = timer => () };');before=events.read_bytes();assert b'operation polled' in before
  os.write(t.master,(dep+'\n').encode())
  if consent:
   until(t,'Continue? [y/N]');os.write(t.master,b'y\n')
  if cancel:
   marker=Path(env.get('RNX_PROJECT_PAUSE_FILE',env.get('RNX_CACHE_MARKER',env.get('TRAP_MARKER'))));stop=time.monotonic()+20
   while not marker.exists() and time.monotonic()<stop:time.sleep(.02)
   assert marker.exists();os.kill(t.p.pid,signal.SIGINT)
  out=t.read(timeout=240);assert expected in out,(label,out)
  assert events.read_bytes()==before,(label,events.read_text()) # No hidden runtime turn.
  assert '42' in t.send('held');release.touch();assert '73' in t.send('q.await');assert 'operation dropped' in events.read_text()
  os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
  (O/(label+'.pty')).write_bytes(t.log);rows[label]=True
 finally:
  (O/(label+'.pty')).write_bytes(t.log);t.close();restore()
for fault in ['dep-author','before-add-rename','after-add-rename','dep-resolve','after-cargo-publication','after-json-publication','dep-build']:
 journey('preserve-'+fault,{'RNX_PROJECT_FAIL':fault})
for label,changes,dep,assoc in [('unknown',{},':dep unknown',ASSOC),('duplicate',{},':dep polars polars',ASSOC),('missing-name',{},':dep',ASSOC),('bad-option',{},':dep --bad polars',ASSOC),('duplicate-offline',{},':dep --offline --offline polars',ASSOC),('custom',{},':dep polars',''),('bad-carrier',{},':dep polars','aa')]:
 journey('preserve-'+label,changes,dep,False,assoc=assoc)
slow_tool=W/'slow-tool';slow_tool.write_text('#!/usr/bin/python3\nimport time\ntime.sleep(120)\n');slow_tool.chmod(0o755)
for label,tool in [('timeout-tool',str(slow_tool)),('missing-tool',str(W/'missing-tool')),('incompatible-tool','/bin/true')]:
 bad=dict(FIELDS);bad[2]=tool
 journey('preserve-'+label,consent=False,assoc=frame(7,bad).hex())
# Real per-key waiter cancellation. Learn the prospective key through real lock.
assert call([T,'add','--manifest',M,'polars']).returncode==0
assert call([T,'lock','--manifest',M,'--offline']).returncode==0
assembly=json.loads((P/'rnx.lock').read_text())['assembly'];(W/'candidate-assembly.json').write_text(json.dumps(assembly,indent=2));key=subprocess.check_output(['/home/me/work/rnx-bench/probes/removal-final/target/b3'],input=assembly['identity'].encode()).decode().strip();restore()
f=open(W/'cache/locks'/(key+'.lock'),'a+');os.fchmod(f.fileno(),0o600);fcntl.flock(f,fcntl.LOCK_EX)
waiter=W/'waiting';waiter.unlink(missing_ok=True)
try:journey('preserve-cache-waiter',{'RNX_CACHE_PAUSE':'waiting','RNX_CACHE_MARKER':str(waiter)},cancel=True)
finally:f.close()
# Real Cargo group ownership, with only compilation substituted by a waiting child.
traps=W/'traps';traps.mkdir(exist_ok=True);trap=traps/'cargo';real=subprocess.check_output(['which','cargo'],text=True).strip();marker2=W/'cargo-started';marker2.unlink(missing_ok=True)
trap.write_text('#!/usr/bin/python3\nimport os,sys,subprocess,time,json\nif "build" in sys.argv[1:]:\n p=subprocess.Popen(["sleep","120"])\n open(os.environ["TRAP_MARKER"],"w").write(json.dumps([os.getpid(),p.pid]))\n p.wait()\nelse: os.execv('+repr(real)+',["cargo"]+sys.argv[1:])\n');trap.chmod(0o755)
journey('preserve-cargo-builder',{'PATH':str(traps)+':'+ENV['PATH'],'TRAP_MARKER':str(marker2)},cancel=True)
pids=json.loads(marker2.read_text());stop=time.monotonic()+5
while any(Path('/proc',str(pid)).exists() and Path('/proc',str(pid),'stat').read_text().split()[2]!='Z' for pid in pids) and time.monotonic()<stop:time.sleep(.02)
assert all(not Path('/proc',str(pid)).exists() or Path('/proc',str(pid),'stat').read_text().split()[2]=='Z' for pid in pids)
rows['cargo_group_no_running_processes_after_cancellation']=pids

marker=W/'pause';marker.unlink(missing_ok=True)
journey('preserve-interrupt',{'RNX_PROJECT_PAUSE':'dep-resolve','RNX_PROJECT_PAUSE_FILE':str(marker)},cancel=True)
for fault in ['before-build','before-attach']:
 journey('preserve-cache-'+fault,{'RNX_CACHE_FAIL':fault})
# Missing scratch setup refuses before allocation. Successful allocation remains
# after an author failure and uses the private persistent directory contract.
scratch_env=dict(ENV,RNX_DEP_RUNTIME=str(W/'native'),XDG_STATE_HOME=str(W/('allocated-state-'+str(time.time_ns()))),RNX_PROJECT_FAIL='dep-author')
p,s,(k,d)=start(request('postgres','',STOCK,''),scratch_env);assert k==2
s.sendall(frame(4,{1:d[1]}));s.shutdown(socket.SHUT_WR);k,e=receive(s);assert k==8 and 'author' in e[1];end(p,s)
scratch=Path(d[3]);assert scratch.is_file() and scratch.stat().st_mode&0o777==0o600 and scratch.parent.stat().st_mode&0o777==0o700 and not scratch.is_relative_to(P)
rows['scratch_private_persistent_after_author_failure']=str(scratch)
missing=dict(ENV);missing.pop('RNX_DEP_RUNTIME',None)
k,e=decline(request('postgres','',STOCK,''),missing);assert k==8 and 'rnx-project runtime install --from /path/to/rnx' in e[1]
rows['scratch_missing_runtime_exact_setup_refusal']=True
p,s,(k,d)=start(request('postgres','',STOCK,''),scratch_env);assert k==2
Path(d[3]).parent.mkdir(parents=True);s.sendall(frame(4,{1:d[1]}));s.shutdown(socket.SHUT_WR);k,e=receive(s);assert k==8 and 'occupied' in e[1];end(p,s)
rows['scratch_reservation_race_refuses_before_authoring']=True
# Canonical user-root symlinks are allowed, but retargeting one after describe
# changes the owning location and cannot silently reuse the old consent.
left=W/('left-'+str(time.time_ns()));right=W/('right-'+str(time.time_ns()));left.mkdir(mode=0o700);right.mkdir(mode=0o700);link=W/('state-link-'+str(time.time_ns()));link.symlink_to(left,target_is_directory=True)
p,s,(k,d)=start(request('postgres','',STOCK,''),dict(scratch_env,XDG_STATE_HOME=str(link)));assert k==2 and d[3].startswith(str(left))
link.unlink();link.symlink_to(right,target_is_directory=True);s.sendall(frame(4,{1:d[1]}));s.shutdown(socket.SHUT_WR);k,e=receive(s);assert k==8 and 'state root changed' in e[1];end(p,s)
assert not (left/'rnx').exists() and not (right/'rnx').exists()
rows['user_root_retarget_requires_new_consent']=True


# Child inherits carrier from a live associated parent, then asks the real tool.
# Its stock roster and executable are both different; no hand-made carrier.
child=W/'child.py';child.write_text("""import os,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('term',"""+repr(str(B/'probes/project-interactive/common.py'))+""");term=importlib.util.module_from_spec(spec);spec.loader.exec_module(term)
assert os.environ['RNX_INTERNAL_SESSION_V1']
t=term.Terminal(["""+repr(str(STOCK))+""",'--no-splash','--color=never'],Path.cwd(),dict(os.environ))
try:
 t.read();out=t.send(':dep polars');assert 'roster mismatch' in out,out
 os.write(t.master,b':q\\n');t.read(False);assert t.p.wait(timeout=5)==0
 print('inherited carrier refused by actual child',flush=True)
finally:t.close()
""")
c=call([T,'session','--manifest',M,'--no-splash','--color=never'],stdin='process::run("/usr/bin/python3", ['+json.dumps(str(child))+'], #{})\n:q\n');assert c.returncode==0 and 'inherited carrier refused by actual child' in c.stdout,(c.stdout,c.stderr)
rows['actual_session_child_inherits_and_refuses_parent_association']=True
c=call([APP,'--no-splash','--color=never'],dict(ENV,RNX_INTERNAL_SESSION_V1=ASSOC),stdin='let held = 42;\n:dep polars\nheld\n:q\n');assert c.returncode==0 and '42' in c.stdout and 'requires a terminal' in c.stderr
rows['nonterminal_does_not_consume_following_input']=True
# Reopen the combined artifact only through ordinary product commands, then
# ask for its already-installed namespace. No consent or second preparation.
assert call([T,'add','--manifest',M,'polars']).returncode==0
assert call([T,'lock','--manifest',M,'--offline']).returncode==0
assert call([T,'build','--manifest',M,'--offline']).returncode==0
snapshot={p:p.read_bytes() for p in [M,P/'rnx.lock',P/'.rnx/receipt.json']}
t=term.Terminal([T,'session','--manifest',M,'--no-splash','--color=never'],P,ENV)
try:
 t.read();t.send('let held = 42;');out=t.send(':dep polars');assert 'already installed; session unchanged' in out and 'Continue?' not in out
 assert '42' in t.send('held');assert all(p.read_bytes()==b for p,b in snapshot.items());os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
finally:t.close();restore()
rows['installed_catalogue_namespace_is_true_noop']=True
assert (R/'src/dep_wire.rs').read_bytes()==(R/'tools/project/src/dep_wire.rs').read_bytes()
rows['protocol_endpoints_are_identical']=True

(O/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n')
print('PASS',len(rows),'preparation groups')
