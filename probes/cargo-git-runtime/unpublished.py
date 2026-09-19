"""Explicit acquisition control; the saved unpushed plan rev is not a release coordinate."""
from common import *
x=T/'unpublished';(x/'src').mkdir(parents=True,exist_ok=True)
rev='d1b4c192e2eec144191af603263c0afbad54cf25'
(x/'Cargo.toml').write_text('[package]\nname="unpublished-coordinate-control"\nversion="0.0.0"\nedition="2024"\n[workspace]\n[dependencies]\nrnx={git="'+URL+'", rev="'+rev+'"}\n')
(x/'src/main.rs').write_text('fn main() {}\n')
p=run(['cargo','metadata','--format-version=1','--manifest-path',x/'Cargo.toml'],ok=False,timeout=120)
assert p.returncode!=0, 'this revision has become available; record the changed control, do not claim failure'
save('unpublished-coordinate.json',{'rev':rev,'url':URL,'status':p.returncode,'stderr':p.stderr.decode(),'meaning':'Clean local HEAD alone does not establish that the configured remote can supply it.'})
