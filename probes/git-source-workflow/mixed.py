from common import *
import shutil
native=T/'mixed-git';(native/'src').mkdir(parents=True);(native/'Cargo.toml').write_text('[package]\nname="fixture-adapter"\nversion="0.0.0"\nedition="2024"\n[workspace]\n');(native/'src/lib.rs').write_text('pub fn build() {}\n');git(native,'init','-q');git(native,'add','.');git(native,'commit','-qm','Git adapter fixture');rev=git(native,'rev-parse','HEAD').stdout.decode().strip()
runtime=T/'mixed-path';shutil.copytree(T/'tiny-source-clean',runtime,ignore=shutil.ignore_patterns('.git'))
f=runtime/'src/lib.rs';f.write_text(f.read_text().replace('pub fn none()->Self{Self}', 'pub fn none()->Self{Self} pub fn with<T>(self,_:&str,_:T)->Self{self}'));git(runtime,'init','-q');git(runtime,'add','.');git(runtime,'commit','-qm','path runtime fixture')
p=T/'mixed-app';p.mkdir();(p/'main.rn').write_text('pub fn main(_) {}\n');(p/'rnx.toml').write_text('format=2\n[application]\nentry="main.rn"\n[runtime]\npath='+json.dumps(str(runtime))+'\n[native.addon]\ngit='+json.dumps(native.as_uri())+'\nrev="'+rev+'"\npackage="fixture-adapter"\nbuilder="build"\nhook="plain"\n')
for op in ['lock','build']:run([TOOL,op,'--manifest',p/'rnx.toml'])
lock=json.loads((p/'rnx.lock').read_text());assert len(lock['git'])==1 and len(lock['inputs']['native']['packages'])==1
rows=[]
for kind,root,leaf in [('path',runtime,'src/lib.rs'),('git',Path(lock['git'][0]['checkout']),'src/lib.rs')]:
 path=root/leaf;old=path.read_bytes();stamp=path.stat();new=old.replace(b'fixture runtime',b'fixture runtimf') if kind=='path' else old.replace(b'build',b'built');assert len(new)==len(old) and new!=old;path.write_bytes(new);os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
 try:
  for verify in [False,True]:
   r=run([TOOL,'eval','--manifest',p/'rnx.toml',*(['--verify'] if verify else []),'--','42'],ok=False);assert (r.returncode==0)==(kind=='git' and not verify),(kind,verify,r.stderr);rows.append({'kind':kind,'verify':verify,'status':r.returncode,'stderr':r.stderr.decode()})
 finally:path.write_bytes(old);os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
# A genuinely external candidate is checked even on the everyday Git path.
config=Path(ENV['RNX_PROJECT_CACHE'])/'.cargo';config.mkdir();file=config/'config.toml';file.write_text('[net]\noffline=true\n')
try:
 r=run([TOOL,'eval','--manifest',T/'tiny-b-clean/rnx.toml','--','42'],ok=False);assert r.returncode and b'inputs changed' in r.stderr,r.stderr;rows.append({'kind':'new-external-config','status':r.returncode,'stderr':r.stderr.decode()})
finally:file.unlink();config.rmdir()
run([TOOL,'eval','--manifest',p/'rnx.toml','--','42']);save('mixed.json',rows);print('Mixed path/Git content policies and external audit pass',flush=True)
