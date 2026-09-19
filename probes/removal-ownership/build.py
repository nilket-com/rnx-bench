from pathlib import Path
import subprocess as sp,shutil,json,hashlib,os
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';P=W/'tool';O=Path(os.environ.get('RNX_REMOVAL_RESULTS',str(B/'results/removal-ownership-0066'))).resolve();O.mkdir(parents=True,exist_ok=True)
P.mkdir(parents=True,exist_ok=True)
shutil.copytree(R/'tools/project/src',P/'src',dirs_exist_ok=True)
for f in ['Cargo.toml','Cargo.lock']:shutil.copy2(R/'tools/project'/f,P/f)
shutil.copy2(R/'rustfmt.toml',P/'rustfmt.toml');shutil.copy2(H/'removal_probe.rs',P/'src/removal_probe.rs')
with (P/'Cargo.toml').open('a') as f:f.write('\n[[bin]]\nname="rnx-removal-probe"\npath="src/removal_probe.rs"\ntest=false\n')
(P/'target').mkdir(exist_ok=True)
if not (P/'target/release').exists() and (R/'tools/project/target/release').exists():sp.run(['cp','-a','--reflink=auto',R/'tools/project/target/release',P/'target/release'],check=True)
for name,args in [('fmt',['cargo','fmt','--manifest-path',P/'Cargo.toml']),('build',['cargo','build','--locked','--offline','--release','--manifest-path',P/'Cargo.toml','--bin','rnx-removal-probe']),('clippy',['cargo','clippy','--locked','--offline','--manifest-path',P/'Cargo.toml','--bin','rnx-removal-probe','--','-D','warnings'])]:
 with (O/(name+'.log')).open('w') as f:p=sp.run(args,stdout=f,stderr=sp.STDOUT)
 assert p.returncode==0,(O/(name+'.log')).read_text();print('PASS',name,flush=True)
shutil.copy2(P/'src/removal_probe.rs',H/'removal_probe.rs')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source={str(p.relative_to(R/'tools/project')):sha(p) for p in (R/'tools/project/src').glob('**/*.rs')}
assert all(sha(P/p)==v for p,v in source.items());assert (P/'Cargo.lock').read_bytes()==(R/'tools/project/Cargo.lock').read_bytes()
(O/'source.json').write_text(json.dumps(dict(baseline=sp.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip(),source_sha256=source,candidate_sha256=sha(H/'removal_probe.rs'),lock_unchanged=True,binary=str(P/'target/release/rnx-removal-probe'),binary_sha256=sha(P/'target/release/rnx-removal-probe')),indent=2)+'\n')
