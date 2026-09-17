"""Instrument only inventory groups in a copy; no production profiling hooks."""
from pathlib import Path
import subprocess,shutil,json,os,statistics,hashlib
B=Path(__file__).resolve().parents[2];R=B.parent/'rnx';H=Path(__file__).resolve().parent;P=H/'target/profile';O=B/'results/project-run-default-0059';P.mkdir(exist_ok=True)
for n in ['Cargo.toml','Cargo.lock']:shutil.copy2(R/'tools/project'/n,P/n)
shutil.copytree(R/'tools/project/src',P/'src',dirs_exist_ok=True)
# Warm independent dependency cache; never build concurrently into product target.
if not (P/'target').exists():
 (P/'target').mkdir();subprocess.run(['cp','-a','--reflink=auto',str(R/'tools/project/target/release'),str(P/'target/release')],check=True)
(P/'src/profile.rs').write_text('''use std::{cell::RefCell,time::Instant};
thread_local!{static DATA:RefCell<Vec<(&'static str,f64)>>=const{RefCell::new(Vec::new())};}
pub fn record(n:&'static str,t:Instant){DATA.with(|d|d.borrow_mut().push((n,t.elapsed().as_secs_f64()*1000.0)));}
#[allow(dead_code)] pub fn emit(){DATA.with(|d|eprintln!("INVENTORY {}",serde_json::to_string(&*d.borrow()).unwrap()));}
''')
for n in ['main.rs','lib.rs','assembly_probe.rs']:
 p=P/'src'/n;p.write_text(p.read_text()+'\nmod profile;\n')
p=P/'src/fingerprint.rs';s=p.read_text();start=s.index('fn git(');b=s.index('{',start);e=s.index('\npub(crate) fn native',b);chunk=s[b+1:e].rstrip();assert chunk.endswith('}');chunk=chunk[:-1];s=s[:b+1]+'\nlet start=std::time::Instant::now();\nlet result=(|| -> Result<Vec<u8>,String> {'+chunk+'})();\ncrate::profile::record("git",start);result\n}\n'+s[e:]
# Only native tree hashing: source roots do not enter this function.
start=s.index('pub(crate) fn native');tail=s[start:];old='\thash_files(&root, paths, allowance)';assert tail.count(old)==1;tail=tail.replace(old,'\tlet start=std::time::Instant::now();let result=hash_files(&root, paths, allowance);crate::profile::record("native_tree_hash",start);result');s=s[:start]+tail;p.write_text(s)
p=P/'src/inventory.rs';s=p.read_text();old='\tlet mut external = BTreeMap::new();';assert s.count(old)==1;s=s.replace(old,'\tlet audit_start=std::time::Instant::now();\n'+old)
# End of ancestor audit before final inventory construction.
pos=s.index('\n\tOk(Inventory {');s=s[:pos]+'\n\tcrate::profile::record("ancestor_audit",audit_start);'+s[pos:];p.write_text(s)
p=P/'src/workflow.rs';s=p.read_text();old='inventory::native(m, &self.stage, &self.base, &cargo_home()?, &mut allowance)';assert s.count(old)==1;s=s.replace(old,'{ let start=std::time::Instant::now(); let result=inventory::native(m, &self.stage, &self.base, &cargo_home()?, &mut allowance); crate::profile::record("native_total",start); result }');s=s.replace('Err(command.exec().to_string())','crate::profile::emit();\n\t\t\tErr(command.exec().to_string())');p.write_text(s)
with (O/'inventory-build.log').open('w') as f:subprocess.run(['cargo','build','--release','--locked','--offline','--bin','rnx-project'],cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
for n in ['fingerprint.rs','inventory.rs','workflow.rs','profile.rs']:(O/('inventory-'+n)).write_bytes((P/'src'/n).read_bytes())
print('inventory copy built',flush=True)
