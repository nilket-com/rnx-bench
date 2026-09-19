"""Build frozen product frontends and the accepted baseline for gate 2."""
from pathlib import Path
import subprocess as sp,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/stock-management-0067'
assert not W.exists(),'move the whole prior target aside, not selected files'
W.mkdir();O.mkdir(parents=True,exist_ok=True);(O/'scripts').mkdir(exist_ok=True)
for name,args,cwd in [
 ('product-build',['cargo','build','--locked','--offline','--features','test-support','--bin','rnx'],R),
 ('compatibility-build',['cargo','build','--locked','--offline','--features','test-support','--bin','rnx-project'],R/'tools/project')]:
 with (O/(name+'.log')).open('w') as f:sp.run(args,cwd=cwd,stdout=f,stderr=sp.STDOUT,check=True)
shutil.copy2(R/'target/debug/rnx',W/'rnx');shutil.copy2(R/'tools/project/target/debug/rnx-project',W/'rnx-project')
# Tiny stdin BLAKE3 helper for the historical matrix's renamed identity hash.
p=W/'b3-source';(p/'src').mkdir(parents=True)
(p/'Cargo.toml').write_text('[package]\nname="b3"\nversion="0.0.0"\nedition="2024"\n[workspace]\n[dependencies]\nblake3="=1.8.7"\n')
(p/'src/main.rs').write_text('use std::io::Read; fn main(){let mut b=Vec::new();std::io::stdin().read_to_end(&mut b).unwrap();println!("{}",blake3::hash(&b));}\n')
with (O/'b3-build.log').open('w') as f:sp.run(['cargo','build','--offline','--release'],cwd=p,stdout=f,stderr=sp.STDOUT,check=True)
shutil.copy2(p/'target/release/b3',W/'b3')
sp.run(['git','worktree','add','--detach',str(W/'baseline'),'4e887b6'],cwd=R,check=True)
for name,cwd,bin in [('baseline-build',W/'baseline','rnx'),('baseline-tool-build',W/'baseline/tools/project','rnx-project')]:
 with (O/(name+'.log')).open('w') as f:sp.run(['cargo','build','--locked','--offline','--features','test-support','--bin',bin],cwd=cwd,stdout=f,stderr=sp.STDOUT,check=True)
