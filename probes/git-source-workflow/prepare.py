from common import *
import shutil
assert not T.exists(),'fresh whole target required'
T.mkdir();O.mkdir(parents=True,exist_ok=True)
(T/'cargo-home').mkdir();(T/'cargo-home/registry').symlink_to(Path.home()/'.cargo/registry',target_is_directory=True)
# Build actual management and support entrypoints; nothing is copied into product sources.
for args in [['cargo','build','--locked','--offline','--features','test-support','--manifest-path',R/'tools/project/Cargo.toml'],['cargo','build','--locked','--offline','--features','test-support','--bin','rnx']]:
 p=run(args,cwd=R,env={k:v for k,v in ENV.items() if k!='RNX_PROJECT_CACHE'});(O/('build-tool.log' if '--manifest-path' in args else 'build-root.log')).write_bytes(p.stderr)
shutil.copy2(R/'tools/project/target/debug/rnx-project',TOOL);shutil.copy2(R/'tools/project/target/debug/rnx-project-assembly-probe',PROBE);shutil.copy2(R/'target/debug/rnx',T/'rnx')
# Preserve exact measured source, including files staged but not committed yet.
patch=run(['git','--no-pager','-c','color.ui=false','diff','--no-ext-diff','HEAD','--binary'],cwd=R).stdout;(O/'product.patch').write_bytes(patch)
save('product.json',{'base':git(R,'rev-parse','HEAD').stdout.decode().strip(),'patch_sha256':sha(patch),'tool_sha256':sha(TOOL.read_bytes()),'runner_sha256':sha((T/'rnx').read_bytes())})
print('Frozen product frontends ready',flush=True)

helper=T/'b3-source';(helper/'src').mkdir(parents=True)
(helper/'Cargo.toml').write_text('[package]\nname="b3"\nversion="0.0.0"\nedition="2024"\n[workspace]\n[dependencies]\nblake3="=1.8.7"\n')
(helper/'src/main.rs').write_text('use std::io::Read;fn main(){let mut b=Vec::new();std::io::stdin().read_to_end(&mut b).unwrap();println!("{}",blake3::hash(&b));}')
p=run(['cargo','build','--offline','--release'],cwd=helper);(O/'b3-build.log').write_bytes(p.stderr);shutil.copy2(helper/'target/release/b3',T/'b3')
