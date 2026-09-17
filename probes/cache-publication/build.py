from pathlib import Path
import shutil,subprocess,hashlib,json
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/cache-publication-0061';P=H/'target/tool'
P.mkdir(parents=True,exist_ok=True)
shutil.copytree(R/'tools/project/src',P/'src',dirs_exist_ok=True)
shutil.copyfile(R/'rustfmt.toml',P/'rustfmt.toml')
for f in ['Cargo.toml','Cargo.lock']:shutil.copyfile(R/'tools/project'/f,P/f)
shutil.copyfile(H/'publication_probe.rs',P/'src/publication_probe.rs')
with (P/'Cargo.toml').open('a') as f:f.write('\n[[bin]]\nname="rnx-cache-publication-probe"\npath="src/publication_probe.rs"\ntest=false\n')
# A separate target avoids interference with ordinary tool builds.
cache=P/'target';cache.mkdir(exist_ok=True)
if not (cache/'release').exists():subprocess.run(['cp','-a','--reflink=auto',str(R/'tools/project/target/release'),str(cache/'release')],check=True)
for name,cmd in [('format',['cargo','fmt','--manifest-path',str(P/'Cargo.toml')]),('build',['cargo','build','--locked','--offline','--release','--manifest-path',str(P/'Cargo.toml'),'--features','test-support','--bin','rnx-cache-publication-probe']),('clippy',['cargo','clippy','--locked','--offline','--manifest-path',str(P/'Cargo.toml'),'--features','test-support','--bin','rnx-cache-publication-probe','--','-D','warnings'])]:
 with (O/(name+'.log')).open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
# Archive the formatted prototype and identify every imported product source.
shutil.copyfile(P/'src/publication_probe.rs',H/'publication_probe.rs')
# cargo fmt formats the isolated product copy too; this must not alter it.
files={}
for f in (R/'tools/project/src').rglob('*.rs'):
 rel=f.relative_to(R/'tools/project');assert f.read_bytes()==(P/rel).read_bytes(),rel;files[str(rel)]=hashlib.sha256(f.read_bytes()).hexdigest()
(O/'imported-sources.json').write_text(json.dumps({'rnx_commit':subprocess.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip(),'files':files},indent=2)+'\n')
print('built isolated prototype; imported product sources unchanged')
