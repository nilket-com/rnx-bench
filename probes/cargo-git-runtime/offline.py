from common import *
import sys, shutil, copy, re
helper=T/'tool/target/release/rnx-project-assembly-probe'
def digest(data):
 f=T/'offline-digest-input';f.write_bytes(data);r=T/'offline-digest-output';run([helper,'digest',f,r]);return r.read_text()
def attach(kind, consumer):
 identity=json.loads((O/(kind+'-identity.json')).read_text())
 app=T/(kind+'-consumer-'+consumer)
 request=json.loads((app/'request.json').read_text())
 assert Path(request['entry'])==app/'main.rn'
 for field in ['manifest','main','cargo_lock_blake3','source_kind']:assert request[field]==identity[field]
 key=digest(json.dumps(identity,sort_keys=True,separators=(',',':')).encode())
 entry=T/'assemblies'/key
 ready=json.loads((entry/'ready.json').read_text())
 assert ready['key']==key
 exe=Path(ready['executable']);assert digest(exe.read_bytes())==ready['artifact_blake3']
 if kind=='git':
  for item in identity['native']:assert item['source'].endswith('#'+REV)
  root=Path(next(p['canonical_root'] for p in identity['native'] if p['name']=='rnx'))
  run([T/'raw-verify',root,REV])
 else:
  # Same existing product inventory, including file content fingerprints and external audit.
  m=T/'path-audit-metadata.json';out=T/'path-attachment-inventory.json'
  run([helper,'audit',m,T/'path-resolver',T/'assemblies',T/'cargo-home',out])
  inv=json.loads(out.read_text());assert inv['trees']==identity['native']['trees'];assert inv['external']==identity['external']
 app=T/(kind+'-consumer-'+consumer)
 p=run([exe,'run',app/'main.rn']);assert p.stdout.decode().strip()==('42' if consumer=='a' else '99')
 return {'kind':kind,'key':key,'output':p.stdout.decode(),'artifact':ready['artifact_blake3']}
if len(sys.argv)>1 and sys.argv[1]=='child':
 save('offline-attachments.json',[attach(k,c) for k in ['git','path'] for c in ['a','b']]);sys.exit(0)
trap=T/'traps';trap.mkdir(exist_ok=True)
script='#!/bin/sh\nprintf "%s\\n" "$0 $*" >> '+str(T/'compiler-attempts')+'\nexit 77\n'
for name in ['cargo','rustc','cc','gcc','clang']:
 p=trap/name;p.write_text(script);p.chmod(0o755)
env=ENV|{'PATH':str(trap)+':'+ENV['PATH']}
control=run(['rustc','--crate-name','positive_control'],env=env,ok=False);assert control.returncode==77
(T/'compiler-attempts').unlink()
prefix=['bwrap','--unshare-user','--uid',str(os.getuid()),'--gid',str(os.getgid()),'--unshare-net','--bind','/','/','--dev','/dev','--proc','/proc','--']
# Assert network isolation itself, not just the --offline spelling.
check='import socket\ns=socket.socket()\ns.settimeout(1)\ntry:s.connect(("1.1.1.1",443))\nexcept OSError:print("network unavailable")\nelse:raise SystemExit(1)'
assert run(prefix+[sys.executable,'-c',check]).stdout.strip()==b'network unavailable'
run(prefix+['strace','-f','-e','trace=process,network','-o',O/'offline.trace',sys.executable,P/'offline.py','child'],env=env)
assert not (T/'compiler-attempts').exists()
trace=(O/'offline.trace').read_text()
execs=re.findall(r'execve\("([^"]+)"',trace)
assert not any(Path(p).name in ['cargo','rustc','cc','gcc','clang'] for p in execs)
assert 'AF_INET' not in trace
# Cached Cargo resolution works offline independently of candidate attachment.
run(prefix+['cargo','metadata','--offline','--locked','--format-version=1','--manifest-path',T/'discovery/Cargo.toml'])
# Empty Git cache cannot resolve the same coordinates offline (registry is pre-populated).
empty=T/'empty-cargo-home';empty.mkdir(exist_ok=True)
if not (empty/'registry').exists():(empty/'registry').symlink_to(Path.home()/'.cargo/registry',target_is_directory=True)
p=run(prefix+['cargo','metadata','--offline','--locked','--format-version=1','--manifest-path',T/'discovery/Cargo.toml'],env=ENV|{'CARGO_HOME':str(empty)},ok=False)
assert p.returncode!=0
save('offline-controls.json',{'network_namespace':'unshare-net; positive external socket fails','compiler_trap_positive':control.returncode,'attachment_compiler_attempts':0,'traced_exec_paths':sorted(set(execs)),'attachment_inet_syscalls':0,'empty_git_cache_status':p.returncode,'empty_git_cache_stderr':p.stderr.decode(),'qualification':'Candidate attachment reads retained full identity and verifies artifact/source. It is not production rnx-project support for Git declarations or a general resolver.'})
# Developer override uses the same fingerprint contract: restored mtime still changes the tree.
f=T/'developer-runtime/README.md';old=f.read_bytes();st=f.stat()
try:
 b=bytearray(old);b[0]^=1;f.write_bytes(b);os.utime(f,ns=(st.st_atime_ns,st.st_mtime_ns))
 try:attach('path','a');raise RuntimeError('missed path edit')
 except AssertionError:pass
finally:f.write_bytes(old);os.utime(f,ns=(st.st_atime_ns,st.st_mtime_ns))
attach('path','a')
print('Offline attachment and path override pass',flush=True)
request=T/'git-consumer-b/request.json';original=request.read_bytes()
try:
 changed=json.loads(original);changed['manifest']=changed['manifest'].replace(REV,'0'*40);request.write_text(json.dumps(changed))
 try:attach('git','b');raise RuntimeError('accepted a different revision request')
 except AssertionError:pass
finally:request.write_bytes(original)
attach('git','b')
save('attachment-mutations.json',{'changed_git_revision_request':'refused before launch','path_same_size_restored_mtime_edit':'refused by product BLAKE3 inventory','restoration':'both attach again'})
