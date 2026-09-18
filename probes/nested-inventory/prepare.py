from pathlib import Path
import subprocess as sp, tarfile,io,json,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/nested-inventory-0065';W.mkdir(exist_ok=True);O.mkdir(exist_ok=True)
P=W/'tool';assert not P.exists();P.mkdir()
base='7b0bb65';data=sp.check_output(['git','-C',R,'archive',base,'tools/project','rustfmt.toml'])
with tarfile.open(fileobj=io.BytesIO(data)) as t:t.extractall(P,filter='data')
P=P/'tools/project';(P/'target').mkdir();sp.run(['cp','-a','--reflink=auto',R/'tools/project/target/release',P/'target/release'],check=True)
q=P/'src/fingerprint.rs';s=q.read_text();s+='\npub(crate) mod candidate;\n';s=s.replace('let before = regular(&path)?;','candidate::before_read(&path)?;\n\tlet before = regular(&path)?;');s=s.replace('let mut content = blake3::Hasher::new();','crate::trace::event(serde_json::json!({"read":path}));\n\tlet mut content = blake3::Hasher::new();');s=s.replace('let digest = content.finalize();','candidate::after_read(&path,&after);\n\tlet digest = content.finalize();');s=s.replace('let mut child = Command::new("git")','crate::trace::event(serde_json::json!({"git":root,"args":args}));\n\tlet mut child = Command::new("git")');q.write_text(s)
(P/'src/fingerprint/candidate.rs').write_bytes((H/'candidate.rs').read_bytes());(P/'src/trace.rs').write_bytes((H/'trace.rs').read_bytes())
modules=(P/'src/assembly_probe.rs').read_text().split('use std::')[0]
(P/'src/nested_probe.rs').write_text(modules+'\nmod trace;\n'+(H/'main.rs').read_text())
# Enable only the isolated copy's workflow, so unchanged product launches can
# exercise the candidate through the real lock/receipt checks.
q=P/'src/inventory.rs';s=q.read_text();old='\tlet mut trees = vec![];\n\tfor root in roots {\n\t\ttrees.push(fingerprint::native(&root, allowance)?);\n\t}'
assert s.count(old)==1;s=s.replace(old,'\tlet trees = fingerprint::candidate::many(roots.into_iter().collect(), allowance)?;');q.write_text(s)
# The shared isolated modules also compile in the product and test targets.
for name in ['main.rs','lib.rs','assembly_probe.rs']:
 q=P/'src'/name;q.write_text(q.read_text()+'\nmod trace;\n')
with (P/'Cargo.toml').open('a') as f:f.write('\n[[bin]]\nname="nested-probe"\npath="src/nested_probe.rs"\ntest=false\n')
for args,name in [(['fmt'],'fmt'),(['build','--release','--locked','--offline','--bin','nested-probe','--bin','rnx-project'],'build')]:
 with (O/(name+'.log')).open('w') as f:sp.run(['cargo',*args,'--manifest-path',P/'Cargo.toml'],stdout=f,stderr=sp.STDOUT,check=True)
(O/'provenance.json').write_text(json.dumps({'base':base,'binary_sha256':hashlib.sha256((P/'target/release/nested-probe').read_bytes()).hexdigest(),'source_sha256':{str(q.relative_to(P)):hashlib.sha256(q.read_bytes()).hexdigest() for q in sorted((P/'src').rglob('*.rs'))}},indent=2)+'\n')
