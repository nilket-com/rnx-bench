"""Archive the accepted tool; add clocks only in an isolated copy."""
from pathlib import Path
import subprocess, shutil, json, hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';P=W/'instrumented';O=B/'results/project-run-cost-0059';O.mkdir(exist_ok=True)
cache=W/'build-cache'
if (P/'target').exists():shutil.move(P/'target',cache)
if P.exists():shutil.rmtree(P)
P.mkdir()
if cache.exists():shutil.move(cache,P/'target')
subprocess.run(['git','archive','HEAD','tools/project'],cwd=R,stdout=(W/'source.tar').open('wb'),check=True)
subprocess.run(['tar','xf',str(W/'source.tar'),'--strip-components=2','-C',str(P)],check=True)
(P/'src/profile.rs').write_text('''use std::{cell::RefCell,time::Instant};
thread_local! {static DATA:RefCell<Vec<(&'static str,f64)>>=const{RefCell::new(Vec::new())};}
pub fn measure<T>(name:&'static str,f:impl FnOnce()->T)->T {let t=Instant::now();let result=f();DATA.with(|d|d.borrow_mut().push((name,t.elapsed().as_secs_f64()*1000.0)));result}
pub fn emit(){DATA.with(|d|eprintln!("PROFILE {}",serde_json::to_string(&*d.borrow()).unwrap()));}
''')
for name in ['main.rs','lib.rs']:
 p=P/'src'/name;p.write_text(p.read_text()+'\nmod profile;\n')
p=P/'src/workflow.rs';s=p.read_text()
def sub(old,new,n=1):
 global s
 assert s.count(old)==n,(old,s.count(old));s=s.replace(old,new)
sub('let project = Project::open(&manifest)?;', 'let project = crate::profile::measure("project_open", || Project::open(&manifest))?;')
# read_lock call exists in build too; wrap its definition for all operations.
sub('fn read_lock(&self) -> Result<(Lock, Vec<u8>), String> {','fn read_lock(&self) -> Result<(Lock, Vec<u8>), String> { crate::profile::measure("lock_pair_read_decode", || {')
sub('Ok((lock, bytes))\n\t}', 'Ok((lock, bytes))\n\t}) }')
sub('let current = Manifest::read(&self.manifest)?;', 'let current = crate::profile::measure("manifest_read", || Manifest::read(&self.manifest))?;')
sub('Handoff::from_project(&self.manifest)? != lock.sources','crate::profile::measure("declaration_map", || Handoff::from_project(&self.manifest))? != lock.sources')
sub('let metadata = self.metadata_for(lock)?;', 'let metadata = crate::profile::measure("reconstruct_metadata", || self.metadata_for(lock))?;')
sub('self.layout(&Handoff::from_project(&self.manifest)?)?;', 'crate::profile::measure("layout_map", || self.layout(&Handoff::from_project(&self.manifest)?))?;')
sub('let source = inventory::sources(&self.manifest, &mut allowance)?;', 'let source = crate::profile::measure("source_inventory", || inventory::sources(&self.manifest, &mut allowance))?;')
sub('.map(|m| inventory::native(m, &self.stage, &self.base, &cargo_home()?, &mut allowance))', '.map(|m| crate::profile::measure("native_inventory", || inventory::native(m, &self.stage, &self.base, &cargo_home()?, &mut allowance)))')
sub('let (cargo, main) = generate::wrapper(&current, &self.base)?;', 'let (cargo, main) = crate::profile::measure("wrapper_identity", || generate::wrapper(&current, &self.base))?;')
sub('let (path, digest) = match &lock.assembly {','let receipt_start = std::time::Instant::now();\n\t\tlet (path, digest) = match &lock.assembly {')
sub('\t\tlet maps = self.dot.join("maps");','\t\tcrate::profile::measure("receipt", || receipt_start.elapsed());\n\t\tlet map_start = std::time::Instant::now();\n\t\tlet maps = self.dot.join("maps");')
# use explicit record to time larger sequential blocks without wrapping control flow.
s=s.replace('crate::profile::measure("receipt", || receipt_start.elapsed());','crate::profile::record("receipt", receipt_start);')
sub('self.atomic(&map, &map_bytes)?;', 'self.atomic(&map, &map_bytes)?;\n\t\tcrate::profile::record("map_publication", map_start);')
sub('Err(command.exec().to_string())','crate::profile::emit();\n\t\t\tErr(command.exec().to_string())')
p.write_text(s)
p=P/'src/profile.rs';p.write_text(p.read_text()+'pub fn record(name:&\'static str,t:Instant){DATA.with(|d|d.borrow_mut().push((name,t.elapsed().as_secs_f64()*1000.0)));}\n')
p=P/'src/assembly.rs';s=p.read_text();old='verify(executable, expected)?;';assert s.count(old)==1;s=s.replace(old,'crate::profile::measure("artifact_fingerprint", || verify(executable, expected))?;');s=s.replace('let mut command = Command::new(executable);','let map_start=std::time::Instant::now();\n\tlet mut command = Command::new(executable);');s=s.replace('command.arg(entry).args(args);','command.arg(entry).args(args);\n\tcrate::profile::record("command_map_check",map_start);');p.write_text(s)
# No clocks touch the hash loop or filesystem verification itself.
with (O/'instrumented-build.log').open('w') as f:subprocess.run(['cargo','build','--release','--locked','--offline','--bin','rnx-project'],cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
for name in ['main.rs','lib.rs','workflow.rs','assembly.rs','profile.rs']:
 shutil.copy2(P/'src'/name,O/('instrumented-'+name))
(O/'provenance.json').write_text(json.dumps({'root':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'lock_sha256':hashlib.sha256((P/'Cargo.lock').read_bytes()).hexdigest(),'binary_sha256':hashlib.sha256((P/'target/release/rnx-project').read_bytes()).hexdigest()},indent=2)+'\n')
print('instrumented copy built',flush=True)
