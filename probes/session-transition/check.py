"""Gate 1: control/ownership and real entry teardown, not a product :dep test."""
from pathlib import Path
import hashlib,importlib.util,json,os,signal,socket,struct,subprocess,sys,tempfile,time
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/session-transition-0063';W=H/'target'
T=W/'tool/target/debug/rnx-transition-tool-probe';APP=W/'root/target/debug/rnx-transition-fixture';STOCK=W/'root/target/debug/rnx'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','CARGO_','RUST'))};rows={};calls=[]
def frame(k,f,version=1):
 b=bytes([version,k])+b''.join(bytes([key])+struct.pack('!I',len(value.encode()))+value.encode() for key,value in sorted(f.items()));return struct.pack('!I',len(b))+b
def exact(sock,n):
 b=b''
 while len(b)<n:
  c=sock.recv(n-len(b));assert c,'premature EOF';b+=c
 return b
def receive(sock):
 n=struct.unpack('!I',exact(sock,4))[0];assert 2<=n<=65536;b=exact(sock,n);assert b[0]==1;k=b[1];i=2;f={}
 while i<len(b):tag=b[i];n=struct.unpack('!I',b[i+1:i+5])[0];i+=5;assert tag not in f;f[tag]=b[i:i+n].decode();i+=n
 assert i==len(b);return k,f
def start(env):
 a,b=socket.socketpair();a.settimeout(6)
 p=subprocess.Popen([T],env=dict(env,RNX_INTERNAL_DEP_FD=str(b.fileno())),pass_fds=(b.fileno(),),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE);b.close();return p,a
def end(p,s):
 s.close();out,err=p.communicate(timeout=6);assert p.returncode==0,(out,err);return out,err
spec=importlib.util.spec_from_file_location('terminal',B/'probes/project-interactive/common.py');terminal=importlib.util.module_from_spec(spec);spec.loader.exec_module(terminal)
with tempfile.TemporaryDirectory(prefix='rnx-dep-gate1-') as tmp:
 w=Path(tmp);n=w/'native';n.mkdir();(n/'Cargo.toml').write_text('[package]\nname="rnx"\n')
 for name in ['polars','postgres']:
  d=n/'adapters'/name;d.mkdir(parents=True);(d/'Cargo.toml').write_text('[package]\nname="rnx-'+name+'"\n[dependencies]\nrnx={path="../.."}\n')
 a=w/'app';a.mkdir();(a/'.rnx').mkdir();m=a/'rnx.toml'
 base='format=1\n[application]\nentry="main.rn"\n[runtime]\npath="../native"\n[native.fixture]\npath="../native"\npackage="fixture"\nbuilder="build"\nhook="lifecycle"\n'
 # Opaque snapshot sentinels deliberately are NOT production readiness proof.
 # Full product receipt/cache validation belongs to preparation integration.
 m.write_text(base);(a/'main.rn').write_text('original');(a/'rnx.lock').write_text('gate1 lock snapshot');(a/'.rnx/receipt.json').write_text('gate1 receipt snapshot')
 def association():return subprocess.check_output([T,'associate',m,APP],text=True).strip()
 assoc=association();state=w/'state';env=dict(ENV,RNX_PROJECT_TOOL=str(T),RNX_DEP_RUNTIME=str(n),XDG_STATE_HOME=str(state),RNX_CONFIG=str(w/'no-config'),RNX_HISTORY=str(w/'history'),TERM='xterm-256color')
 replacement=w/'replacement';replacement.write_text('#!/usr/bin/python3\nimport os\nwith open(os.environ["RNX_PROBE_EVENTS"],"a") as f:f.write("replacement pid="+str(os.getpid())+"\\n")\nprint("replacement reached",flush=True)\n');replacement.chmod(0o755);env['RNX_PROBE_REPLACEMENT']=str(replacement)
 def request(names='polars',capsule=assoc,exe=APP,installed='fixture'):return {1:names,2:capsule,3:str(exe),4:installed,5:'offline'}
 # Different application bytes do not change association; runtime/native declarations do.
 p,s=start(env);s.sendall(frame(1,request()));k,d=receive(s);assert k==2 and d[5]=='polars' and d[7]=='offline' and '100 seconds' in d[2];assert not state.exists();s.sendall(frame(3,{}));end(p,s)
 old=m.read_bytes();(a/'main.rn').write_text('source edited')
 p,s=start(env);s.sendall(frame(1,request()));k,e=receive(s);assert k==2 and d==e;s.sendall(frame(3,{}));end(p,s)
 for f,new in [(m,base.replace('builder="build"','builder="changed"')),(a/'rnx.lock','replacement lock'),(a/'.rnx/receipt.json','replacement receipt')]:
  saved=f.read_bytes();f.write_text(new);p,s=start(env);s.sendall(frame(1,request()));k,e=receive(s);assert k==8 and 'stale' in e[1];end(p,s);f.write_bytes(saved)
 p,s=start(env);s.sendall(frame(1,request(installed='other')));k,e=receive(s);assert k==8 and 'stale' in e[1];end(p,s)
 rows['association_source_change_allowed_declaration_receipt_lock_roster_changes_refuse']=True
 # Changed describe cannot be silently consented; even a comment changes this token.
 p,s=start(env);s.sendall(frame(1,request()));k,d=receive(s);m.write_text(base+'# editor\n');s.sendall(frame(4,{1:d[1]}));k,e=receive(s);assert k==8 and 'description changed' in e[1];end(p,s);m.write_bytes(old)
 rows['description_rechecked_before_prepare']=True
 # Describe is read-only and cost facts come from the selected entry.
 for name in ['polars','postgres']:
  p,s=start(env);s.sendall(frame(1,request(name,'',STOCK,'')));k,d=receive(s);assert k==2 and ('100 seconds' in d[2])==(name=='polars') and not state.exists();s.sendall(frame(3,{}));end(p,s)
 rows['scratch_describe_decline_no_writes_and_entry_specific_costs']=True
 p,s=start(env);s.sendall(frame(1,request('polars','',STOCK,'')));k,d=receive(s);assert k==2;s.sendall(frame(4,{1:d[1]}));k,e=receive(s);assert k==5;end(p,s);scratch=Path(d[3]);assert scratch.exists() and scratch.parent.stat().st_mode&0o777==0o700 and scratch.stat().st_mode&0o777==0o600
 # A positive inherited-fd control proves the same observer can see a leak.
 left,right=socket.socketpair();fd=right.fileno()
 control=subprocess.run(['/usr/bin/python3','-c',f'import os; os.fstat({fd}); raise SystemExit(91)'],pass_fds=(fd,));assert control.returncode==91;left.close();right.close()
 rows['scratch_exclusive_private_allocation_and_child_descriptor_seal']=True
 # An existing reservation, managed symlink or FIFO is never reused.
 for kind in ['existing','symlink','fifo']:
  selected=w/('state-'+kind);selected.mkdir();(selected/'rnx').mkdir();sessions=selected/'rnx/sessions';sessions.mkdir();target=sessions/'gate1-session'
  if kind=='existing':target.mkdir()
  elif kind=='symlink':target.symlink_to(a,target_is_directory=True)
  else:os.mkfifo(target)
  p,s=start(dict(env,XDG_STATE_HOME=str(selected)));s.sendall(frame(1,request('polars','',STOCK,'')));k,d=receive(s);assert k==2;s.sendall(frame(4,{1:d[1]}));k,e=receive(s);assert k==8;end(p,s)
 rows['scratch_taken_symlink_fifo_refuse']=True
 real=w/'moved-state';real.mkdir();link=w/'state-link';link.symlink_to(real,target_is_directory=True)
 p,s=start(dict(env,XDG_STATE_HOME=str(link)));s.sendall(frame(1,request('polars','',STOCK,'')));k,d=receive(s);assert k==2 and d[3].startswith(str(real));s.sendall(frame(4,{1:d[1]}));assert receive(s)[0]==5;end(p,s)
 p,s=start(dict(env,XDG_STATE_HOME=str(n/'state')));s.sendall(frame(1,request('polars','',STOCK,'')));k,e=receive(s);assert k==8 and 'native roots contain' in e[1];end(p,s)
 p,s=start(dict(env,XDG_STATE_HOME=str(w)));s.sendall(frame(1,request('polars','',STOCK,'')));k,e=receive(s);assert k==8 and 'native roots contain' in e[1];end(p,s)
 rows['user_root_symlink_canonicalized_native_containment_refused']=True
 # Framing controls, including lengths refused without waiting for their payload.
 malformed=[b'\xff\xff\xff\xff',frame(1,request(),2),frame(99,{}),frame(1,{**request(),12:'unknown'}),struct.pack('!I',12)+b'\1\1\1\0\0\0\0\1\0\0\0\0',frame(1,request())[:-1]]
 for blob in malformed:
  p,s=start(env);s.sendall(blob);s.shutdown(socket.SHUT_WR);k,e=receive(s);assert k==8;end(p,s)
 p,s=start(env);s.sendall(frame(1,request(capsule=assoc+'00')));assert receive(s)[0]==8;end(p,s)
 rows['version_length_unknown_duplicate_truncated_and_trailing_capsule_refusals']=True
 # Actual entry stack / lifecycle fixture: pending operation is polled by Rune.
 def journey(label,*,consent='yes',replacement_path=replacement,panic=False,edit=False,association_value=assoc,tool=T):
  events=w/(label+'.events');e=dict(env,RNX_INTERNAL_SESSION_V1=association_value,RNX_PROJECT_TOOL=str(tool),RNX_PROBE_EVENTS=str(events),RNX_PROBE_CONSENT=consent,RNX_PROBE_REPLACEMENT=str(replacement_path))
  if edit:e['RNX_PROBE_EDIT']=str(m)
  t=terminal.Terminal([APP,'--no-splash','--color=never'],a,e)
  try:
   t.read();pid=t.p.pid;t.send('let held = 42; let value = fixture::value(); let q = fixture::pending('+str(panic).lower()+');')
   t.send('let timer = time::sleep(5); select { _ = q => (), _ = timer => () };')
   assert events.read_text().splitlines()==['operation polled']
   os.write(t.master,b':dep --offline polars\n')
   if consent!='yes' or edit or not association_value:
    out=t.read();assert 'restart is beginning' not in out;assert '42' in t.send('held');assert events.read_text().splitlines()==['operation polled'];t.send('let timer2 = time::sleep(5); select { _ = q => (), _ = timer2 => () };');assert events.read_text().splitlines()==['operation polled'];os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
   else:
    out=t.read(False);status=t.p.wait(timeout=5)
    assert 'restart is beginning' in out
    if panic or replacement_path!=replacement:assert status!=0 and 'replacement reached' not in out
    else:assert status==0 and 'replacement reached' in out
   trace=events.read_text().splitlines();assert trace.index('operation dropped')<trace.index('entry stack returned') and trace.index('value dropped')<trace.index('entry stack returned') and trace.index('context dropped')<trace.index('entry stack returned')
   if not panic and consent=='yes' and not edit and association_value:
    assert trace.index('entry stack returned')<trace.index('before exec')
    if replacement_path==replacement:assert trace[-1]=='replacement pid='+str(pid)
   else:assert 'before exec' not in trace
   (O/(label+'.json')).write_text(json.dumps({'pid':pid,'events':trace,'status':t.p.returncode},indent=2)+'\n')
  finally:
   (O/(label+'.pty.bin')).write_bytes(t.log);(O/(label+'.pty.txt')).write_text('\n'.join(x.rstrip() for x in terminal.text(t.log).splitlines())+'\n');t.close();m.write_text(base)
 journey('decline',consent='no');journey('changed-prepare',edit=True);journey('unassociated-custom',association_value='');journey('handover');journey('cleanup-failure',panic=True);journey('exec-failure',replacement_path=w/'missing-executable')
 rows['real_rune_polled_resource_survives_precommit_and_drops_before_exec']=True
 rows['cleanup_and_exec_failure_end_without_retired_prompt']=True
 rows['exec_preserves_pid_after_entry_stack_unwinds']=True
 # Ordinary stock driver selection: PATH fallback, missing and old helper.
 bin=w/'bin';bin.mkdir();(bin/'rnx-project').symlink_to(T)
 for label,extra in [('path',dict(PATH=str(bin)+':'+ENV['PATH'])),('missing',dict(PATH=str(w/'no-path'))),('incompatible',dict(RNX_PROJECT_TOOL='/usr/bin/false'))]:
  e=dict(env,RNX_PROBE_CONSENT='no',RNX_PROBE_EVENTS=str(w/(label+'.events')));e.pop('RNX_PROJECT_TOOL');e.update(extra)
  p=subprocess.run([STOCK,'--no-splash','--color=never'],input='let held=42;\n:dep postgres\nheld\n:q\n',env=e,cwd=a,capture_output=True,text=True,timeout=10)
  assert p.returncode==0 and '42' in p.stdout
  if label=='path':assert 'Cargo mode:' in p.stdout and '100 seconds' not in p.stdout
  else:assert 'refused' in p.stderr
 rows['stock_tool_path_missing_and_incompatible_preserve_session']=True
(O/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
print('PASS',len(rows),'ownership/protocol/handover groups; gate 1 only')
