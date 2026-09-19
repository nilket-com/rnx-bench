from pathlib import Path
import subprocess as sp,shutil,json,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/removal-final-0066'
rows={}
for mode,flags in [('ordinary',[]),('support',['--features','test-support'])]:
 p=sp.run(['cargo','build','--locked','--offline','--release','--manifest-path',str(R/'tools/project/Cargo.toml'),'--bin','rnx-project',*flags],capture_output=True,text=True);(O/(mode+'-release.log')).write_text(p.stdout+p.stderr);assert p.returncode==0
 dst=W/('tool-'+mode);shutil.copy2(R/'tools/project/target/release/rnx-project',dst);rows[mode]=dict(path=str(dst),sha256=hashlib.sha256(dst.read_bytes()).hexdigest())
rlib=next((R/'tools/project/target/release/deps').glob('libblake3-*.rlib'))
sp.run(['rustc',str(H/'b3.rs'),'--edition=2024','-L','dependency='+str(rlib.parent),'--extern','blake3='+str(rlib),'-o',str(W/'b3')],check=True)
(O/'binaries.json').write_text(json.dumps(rows,indent=2)+'\n')
