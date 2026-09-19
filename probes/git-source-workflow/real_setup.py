from common import *
import shutil
S=T/'real-source';origin=T/'origin.git'
assert not S.exists(),'real fixture origin requires a fresh source'
run(['git','clone','--quiet','--no-hardlinks',R,S]);git(S,'checkout','--quiet','--detach',json.loads((O/'product.json').read_text())['base'])
git(S,'apply','--index',O/'product.patch')
run(['git','init','--bare','--quiet',origin]);url=origin.as_uri()
p=S/'Cargo.toml';p.write_text(p.read_text().replace('repository = "https://github.com/nilket-com/rnx"',f'repository = "{url}"'))
git(S,'add','.');git(S,'commit','-qm','fixture: gate-three product with fetchable coordinates');rev=git(S,'rev-parse','HEAD').stdout.decode().strip();git(S,'push','--quiet',url,'HEAD:refs/heads/main')
git(S,'bundle','create',O/'fixture.bundle','HEAD','^'+json.loads((O/'product.json').read_text())['base'])
# A distinct install home proves the consumer's Git cache starts without this source.
home=T/'install-cargo';home.mkdir();(home/'registry').symlink_to(Path.home()/'.cargo/registry',target_is_directory=True)
start=time.monotonic();p=run(['cargo','install','--git',url,'--rev',rev,'rnx','--locked','--jobs','4','--root',T/'installed','--target-dir',T/'install-target'],env=ENV|{'CARGO_HOME':str(home)},timeout=1800)
(O/'git-install.log').write_bytes(p.stderr)
assert sorted(x.name for x in (T/'installed/bin').iterdir())==['rnx']
exe=T/'installed/bin/rnx';run([exe,'project','adapters'])
save('real-setup.json',{'url':url,'rev':rev,'exe':str(exe),'install_seconds':time.monotonic()-start,'exe_sha256':sha(exe.read_bytes()),'fixture_manifest_change':'repository URL only, to local origin','checkout':str(S)})
print('Acquired one-program Git installation ready',flush=True)
