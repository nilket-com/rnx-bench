"""Cargo owns repair during lock; verification never does."""
from common import *
import shutil,shlex
p=T/'tiny-a-clean';lock=json.loads((p/'rnx.lock').read_text());root=Path(lock['git'][0]['checkout']);rev=lock['git'][0]['revision'];f=root/'src/lib.rs';marker=root/'.cargo-ok';original=f.read_bytes();old_marker=marker.read_bytes();edited=original.replace(b'fixture runtime',b'fixture runtimf');rows=[]
def locking(env=ENV):return run([TOOL,'lock','--offline','--manifest',p/'rnx.toml'],env=env,ok=False)
def pair():return [(p/n).read_bytes() for n in ['rnx.lock','rnx.Cargo.lock']]
try:
 for cause in ['missing-marker','different-head']:
  f.write_bytes(edited)
  if cause=='missing-marker':marker.unlink()
  else:
   git(root,'add','src/lib.rs');git(root,'commit','-qm','fixture altered HEAD')
  r=locking();assert r.returncode==0,r.stderr
  assert b'Cargo reacquired Git checkout' in r.stderr and f.read_bytes()==original,r.stderr
  assert git(root,'rev-parse','HEAD').stdout.decode().strip()==rev
  rows.append({'case':cause,'status':r.returncode,'report':r.stderr.decode()})
 # A fresh marker is not content authentication. Cargo leaves this edit alone.
 before=pair();f.write_bytes(edited);r=locking();assert r.returncode and b'raw Git blob differs' in r.stderr;assert pair()==before and f.read_bytes()==edited
 rows.append({'case':'fresh-marker-edit-refuses-after-cargo','status':r.returncode})
 f.write_bytes(original)
 # Corrupt a byte AFTER Cargo successfully re-checks out, before rnx verifies.
 trap=T/'post-cargo-trap';trap.mkdir();actual=shutil.which('cargo',path=ENV['PATH']);wrapper=trap/'cargo'
 wrapper.write_text('#!/bin/sh\n'+shlex.quote(actual)+' "$@"\ns=$?\nif [ "$s" -eq 0 ] && [ "$1" = metadata ]; then\n printf "// injected after Cargo\\n" >> '+shlex.quote(str(f))+'\nfi\nexit "$s"\n');wrapper.chmod(0o700)
 marker.unlink();before=pair();r=locking(ENV|{'PATH':str(trap)+':'+ENV['PATH']});assert r.returncode and b'Cargo reacquired Git checkout' in r.stderr,r.stderr;assert pair()==before and f.read_bytes()!=original
 rows.append({'case':'post-reset-mismatch-refuses-no-publication','status':r.returncode,'report':r.stderr.decode()})
 f.write_bytes(original);marker.write_bytes(old_marker)
 # These operations must refuse without resetting even when the marker is absent.
 for args in [['eval','--verify','--','42'],['build','--offline']]:
  f.write_bytes(edited);marker.unlink(missing_ok=True);before=pair()
  r=run([TOOL,*args[:1],'--manifest',p/'rnx.toml',*args[1:]],ok=False)
  assert r.returncode and f.read_bytes()==edited and not marker.exists() and pair()==before,r.stderr
  assert b'lock --manifest' in r.stderr,r.stderr
  rows.append({'case':'refuse-only-'+args[0],'status':r.returncode,'reason':r.stderr.decode()})
finally:
 f.write_bytes(original);marker.write_bytes(old_marker)
run([TOOL,'build','--offline','--manifest',p/'rnx.toml'])
save('acquisition.json',rows);print(len(rows),'acquisition/verification cases pass',flush=True)
