from common import *
import shutil,copy,stat
S=T/'tiny-source-clean';(S/'src').mkdir(parents=True)
(S/'Cargo.toml').write_text('[package]\nname="rnx"\nversion="0.0.0"\nedition="2024"\n[workspace]\n[features]\ncount-allocations=[]\nproject-sources=[]\n')
(S/'src/lib.rs').write_text('pub struct Extensions; impl Extensions{pub fn none()->Self{Self}} pub fn main_with(_:Extensions)->Result<(),Box<dyn std::error::Error>>{println!("fixture runtime");Ok(())}\n')
(S/'.gitignore').write_text('target/\n')
git(S,'init','-q');git(S,'add','.');git(S,'commit','-qm','fixture runtime');rev=git(S,'rev-parse','HEAD').stdout.decode().strip()
p=project('tiny-a-clean',S.as_uri(),rev);run([TOOL,'lock','--manifest',p/'rnx.toml']);run([TOOL,'build','--offline','--manifest',p/'rnx.toml'])
lock=json.loads((p/'rnx.lock').read_text());identity=json.loads(lock['assembly']['identity']);receipt=json.loads((p/'.rnx/receipt.json').read_text());root=Path(lock['git'][0]['checkout']);assert lock['format']==4 and identity['format']==3 and receipt['format']==5
rows=[]
def launch(verify=False):return run([TOOL,'eval','--manifest',p/'rnx.toml',*(['--verify'] if verify else []),'--','42'],ok=False)
def case(name,change,restore,default=True,verified=False):
 before=sha((p/'.rnx/receipt.json').read_bytes());change()
 try:
  a,b=launch(),launch(True);assert (a.returncode==0)==default,(name,a.stderr);assert (b.returncode==0)==verified,(name,b.stderr)
  assert sha((p/'.rnx/receipt.json').read_bytes())==before
  rows.append({'case':name,'default':a.returncode,'verify':b.returncode,'reason':b.stderr.decode()})
 finally:restore()
f=root/'src/lib.rs';old=f.read_bytes();stamp=f.stat();marker_original=(root/'.cargo-ok').read_bytes()
def edit():f.write_bytes(old.replace(b'fixture runtime',b'fixture runtimf'));os.utime(f,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
case('restored-mtime-native-edit-documented-miss',edit,lambda:f.write_bytes(old))
case('untracked',lambda:(root/'extra').write_text('x'),lambda:(root/'extra').unlink())
case('root-marker',lambda:(root/'.cargo-ok').write_text('transport'),lambda:(root/'.cargo-ok').write_bytes(marker_original),verified=True)
case('oversize-marker',lambda:(root/'.cargo-ok').write_bytes(b'x'*4097),lambda:((root/'.cargo-ok').unlink(),(root/'.cargo-ok').write_bytes(marker_original)))
case('marker-symlink',lambda:((root/'.cargo-ok').unlink(),(root/'.cargo-ok').symlink_to(f)),lambda:((root/'.cargo-ok').unlink(),(root/'.cargo-ok').write_bytes(marker_original)))
case('nested-marker',lambda:(root/'src/.cargo-ok').write_text('x'),lambda:(root/'src/.cargo-ok').unlink())
mode=f.stat().st_mode;case('mode-change',lambda:f.chmod(mode|0o111),lambda:f.chmod(mode))
case('tracked-symlink',lambda:(f.unlink(),f.symlink_to(S/'src/lib.rs')),lambda:(f.unlink(),f.write_bytes(old)))
case('tracked-fifo',lambda:(f.unlink(),os.mkfifo(f)),lambda:(f.unlink(),f.write_bytes(old)))
case('staged-delete',lambda:git(root,'rm','--cached','-q','src/lib.rs'),lambda:git(root,'reset','--quiet',rev,'--','src/lib.rs'))
# Full operations refuse before attaching or compiling, without replacing bytes.
edit()
try:
 for operation in ['lock','build']:
  before=(p/'rnx.lock').read_bytes();r=run([TOOL,operation,'--offline','--manifest',p/'rnx.toml'],ok=False);assert r.returncode and b'raw Git blob differs' in r.stderr;assert before==(p/'rnx.lock').read_bytes();rows.append({'case':operation+'-edited-checkout','status':r.returncode})
finally:f.write_bytes(old)
run([TOOL,'build','--offline','--manifest',p/'rnx.toml'])
# A second distinct application attaches with real compiler invocation traps.
q=project('tiny-b-clean',S.as_uri(),rev);run([TOOL,'lock','--offline','--manifest',q/'rnx.toml']);assert json.loads((q/'rnx.lock').read_text())['assembly']==lock['assembly']
traps=T/'traps-clean';traps.mkdir();rustc=shutil.which('rustc',path=ENV['PATH']);cargo=shutil.which('cargo',path=ENV['PATH'])
for name,exe in [('rustc',rustc),('cargo',cargo)]:
 path=traps/name;path.write_text(f'#!/bin/sh\ncase "$1" in -V|-Vv) exec {json.dumps(exe)} "$@";; *) echo forbidden-{name} >&2; exit 98;; esac\n');path.chmod(0o700)
trapped=ENV|{'PATH':str(traps)+':'+ENV['PATH']};run([TOOL,'build','--offline','--manifest',q/'rnx.toml'],env=trapped)
for name in ['cargo','git','rustc']:
 path=traps/name;path.write_text('#!/bin/sh\necho forbidden-launch >&2\nexit 98\n');path.chmod(0o700)
run([TOOL,'eval','--manifest',q/'rnx.toml','--','42'],env=trapped)
trace=O/'everyday.trace';run(['strace','-f','-qq','-o',trace,'-e','trace=execve,openat,connect',TOOL,'eval','--manifest',q/'rnx.toml','--','42'],env=trapped)
text=trace.read_text();assert not any('execve(' in line and any('/'+name+'"' in line for name in ['cargo','rustc','git']) for line in text.splitlines());assert not any('openat(' in line and str(root)+'/' in line for line in text.splitlines());assert 'AF_INET' not in text
rows.append({'case':'second-consumer-offline-attach-and-traced-launch','same_key':True,'compiler_trapped':True,'native_content_opens':0})
save('contracts.json',rows);print(len(rows),'contract groups pass',flush=True)
