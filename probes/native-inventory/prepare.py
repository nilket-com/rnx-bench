"""Frozen product plus clock-only copy; full copied third adapter, no root edits."""
from pathlib import Path
import subprocess as sp,shutil,json,hashlib,os,io,tarfile
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/native-inventory-0065'
assert not W.exists();W.mkdir();O.mkdir(exist_ok=True)
assert not sp.check_output(['git','-C',R,'status','--porcelain','--untracked-files=normal'])
base=sp.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip()
e={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','GIT_','CARGO_','RUST'))};e.update(PYTHONDONTWRITEBYTECODE='1',POLARS_MAX_THREADS='1',CARGO_NET_OFFLINE='true')
# CARGO_NET_OFFLINE is used for tool compilation only, not product commands.
def run(a,log,cwd=None):
 with (O/log).open('w') as f:sp.run(list(map(str,a)),cwd=cwd,env=e,stdout=f,stderr=sp.STDOUT,check=True)
for name in ['stock','timed']:
 p=W/name;p.mkdir()
 data=sp.check_output(['git','-C',R,'archive',base,'tools/project','rustfmt.toml'])
 with tarfile.open(fileobj=io.BytesIO(data)) as t:t.extractall(p,filter='data')
 p=p/'tools/project'
 # Warm the Cargo target without borrowing executable identity or source inputs.
 (p/'target').mkdir();sp.run(['cp','-a','--reflink=auto',R/'tools/project/target/release',p/'target/release'],check=True)
p=W/'timed/tools/project';(p/'src/profile.rs').write_bytes((H/'profile.rs').read_bytes())
for n in ['main.rs','lib.rs','assembly_probe.rs']:
 q=p/'src'/n;q.write_text(q.read_text()+'\nmod profile;\n')
q=p/'src/fingerprint.rs';s=q.read_text()
def change(old,new,n=1):
 global s
 assert s.count(old)==n,(old,s.count(old));s=s.replace(old,new)
# Start one owner at each actual native tree, also in a parent Git repository.
change('let root = root(path)?;\n\tif !git(', 'let _owner=crate::profile::owner(path);\n\tlet root = root(path)?;\n\tif !git(')
change('fn git(root: &Path, args: &[&str], limit: usize) -> Result<Vec<u8>, String> {', 'fn git(root: &Path, args: &[&str], limit: usize) -> Result<Vec<u8>, String> {\nlet phase=if args[0]=="rev-parse" {"git_submodule"} else if args.contains(&"--others") {"git_untracked"} else {"git_tracked"};\nlet t=crate::profile::start();')
change('\tOk(bytes)\n}\npub(crate) fn native', '\tcrate::profile::tree_record(phase,t);\n\tOk(bytes)\n}\npub(crate) fn native')
old='\thash_files(&root, paths, allowance)';pos=s.index('pub(crate) fn native_using');a=s[:pos];z=s[pos:];assert z.count(old)==1;z=z.replace(old,'\tlet t=crate::profile::start();let result=hash_files(&root, paths, allowance);crate::profile::tree_record("tree_total",t);result');s=a+z
change('\tcomponents_no_links(root, &relative)?;', '\tlet path_t=crate::profile::start();\n\tcomponents_no_links(root, &relative)?;')
change('\tlet mut options = fs::OpenOptions::new();','\tcrate::profile::tree_record("path_metadata",path_t);let open_t=crate::profile::start();\n\tlet mut options = fs::OpenOptions::new();')
change('\tif let Some(tree) = tree.as_mut() {\n\t\ttree.update((name.len()', '\tcrate::profile::tree_record("open_metadata",open_t);\n\tif let Some(tree) = tree.as_mut() {\n\t\ttree.update((name.len()')
change('\t\tlet n = file.read(&mut buffer[..take]).map_err(|e| fail(&path, e))?;', '\t\tlet read_t=crate::profile::start();\n\t\tlet n = file.read(&mut buffer[..take]).map_err(|e| fail(&path, e))?;\n\t\tcrate::profile::tree_record("read",read_t);')
change('\t\tif let Some(tree) = tree.as_mut() {\n\t\t\ttree.update(&buffer[..n]);', '\t\tlet hash_t=crate::profile::start();\n\t\tif let Some(tree) = tree.as_mut() {\n\t\t\ttree.update(&buffer[..n]);')
change('\t\tcontent.update(&buffer[..n]);','\t\tcontent.update(&buffer[..n]);\n\t\tcrate::profile::tree_record("digest",hash_t);')
q.write_text(s)
q=p/'src/inventory.rs';s=q.read_text();needle='\tif metadata.len() > input::DOCUMENT_LIMIT {';assert s.count(needle)==1;s=s.replace(needle,'\tlet _total=crate::profile::span("inventory_total".into());\n'+needle)
needle='\tlet mut external = BTreeMap::new();';s=s.replace(needle,'\tlet audit_t=crate::profile::start();\n'+needle)
needle='\t\tabsolute(&path)?;\n\t\tlet file =';s=s.replace(needle,'\t\tabsolute(&path)?;\n\t\tlet owner=trees.iter().filter(|t|path.starts_with(&t.root)).max_by_key(|t|t.root.components().count()).map(|t|t.root.to_string_lossy().into_owned()).unwrap_or_else(||"shared".into());\n\t\tlet _candidate=crate::profile::span(format!("audit|{owner}"));\n\t\tlet file =')
needle='\n\tOk(Inventory {';s=s.replace(needle,'\n\tcrate::profile::record("audit_total",audit_t);'+needle);q.write_text(s)
q=p/'src/workflow.rs';s=q.read_text();needle='Err(command.exec().to_string())';assert s.count(needle)==1;s=s.replace(needle,'crate::profile::emit();\n\t\t\t'+needle);q.write_text(s)
# Fixed-target probe imports the same modules. No manifest/receipt is fabricated.
modules=(p/'src/assembly_probe.rs').read_text().split('use std::')[0]
main=r'''
use std::{path::PathBuf,process::Command};
use sha2::{Digest,Sha256};
#[derive(serde::Deserialize)] struct Config {metadata:serde_json::Value,stage:PathBuf,invocation:PathBuf,home:PathBuf,expected:Option<String>,executable:PathBuf}
fn main()->Result<(),Box<dyn std::error::Error>> {
 let path=std::env::args_os().nth(1).ok_or("config required")?;
 let config:Config=serde_json::from_slice(&std::fs::read(path)?)?;
 let t=std::time::Instant::now();
 let inv=inventory::native(&serde_json::to_vec(&config.metadata)?,&config.stage,&config.invocation,&config.home,&mut fingerprint::Allowance::default())?;
 let inventory_ms=t.elapsed().as_secs_f64()*1000.0;
 let bytes=serde_json::to_vec(&inv)?;let digest=format!("{:x}",Sha256::digest(&bytes));
 if let Some(expected)=config.expected {assert_eq!(digest,expected);profile::emit();eprintln!("INVENTORY_RESULT {digest} {inventory_ms}");
 use std::os::unix::process::CommandExt;
 return Err(Command::new(config.executable).args(["--no-splash","--color=never","eval","42"]).exec().into());}
 println!("{}",serde_json::to_string(&serde_json::json!({"digest":digest,"inventory":inv}))?);Ok(())
}
'''
for name in ['stock','timed']:
 p=W/name/'tools/project';text=modules+main
 if name=='stock':text=text.replace('profile::emit();','')
 else:text+='\nmod profile;\n'
 (p/'src/inventory_probe.rs').write_text(text)
 with (p/'Cargo.toml').open('a') as f:f.write('\n[[bin]]\nname="inventory-probe"\npath="src/inventory_probe.rs"\ntest=false\n')
 run(['cargo','fmt','--manifest-path',p/'Cargo.toml'],name+'-fmt.log')
 run(['cargo','build','--release','--locked','--offline','--manifest-path',p/'Cargo.toml','--bin','rnx-project','--bin','inventory-probe'],name+'-build.log')
# Snapshot source layout, then a complete renamed PostgreSQL adapter within it.
root=W/'s';root.mkdir()
with tarfile.open(fileobj=io.BytesIO(sp.check_output(['git','-C',R,'archive',base]))) as t:t.extractall(root,filter='data')
shutil.copytree(root/'adapters/postgres',root/'adapters/pgcopy')
changed=[]
for q in (root/'adapters/pgcopy').rglob('*'):
 if q.is_file() and (q.suffix=='.rs' or q.name in ['Cargo.toml','Cargo.lock']):
  before=q.read_text();after=before.replace('rnx-postgres','rnx-pgcopy').replace('rnx_postgres','rnx_pgcopy').replace('postgres::query','pgcopy::query')
  if before!=after:q.write_text(after);changed.append(str(q.relative_to(root)))
layouts={'shallow':root,'deep':W/'a/b/c/d/e/f/g/h'/('d'*40),'long':W/('l'*(len(str(W/'a/b/c/d/e/f/g/h'/('d'*40)))-len(str(W))-1))}
for name,d in layouts.items():
 if d!=root:shutil.copytree(root,d)
 for cmd in [['git','init','-q',d],['git','-C',d,'add','.']]:sp.run(cmd,env=e,check=True)
# Keep the fixed target byte-identical for every row; product controls use their own direct artifact.
shutil.copy2(R/'target/release/rnx',W/'fixed-rnx')
(O/'provenance.json').write_text(json.dumps(dict(base=base,renamed_files=changed,layouts={k:str(v) for k,v in layouts.items()},fixed_sha256=hashlib.sha256((W/'fixed-rnx').read_bytes()).hexdigest()),indent=2)+'\n')
# Archive exact modified/new tool files and the patch; unchanged inputs are the published baseline.
for name in ['stock','timed']:
 p=W/name/'tools/project';dest=O/name;dest.mkdir()
 for q in p.rglob('*.rs'):
  if 'target' in q.relative_to(p).parts:continue
  orig=R/'tools/project'/q.relative_to(p)
  if not orig.exists() or orig.read_bytes()!=q.read_bytes():
   out=dest/q.relative_to(p);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(q.read_bytes())
 shutil.copy2(p/'Cargo.toml',dest/'Cargo.toml')
 assert (p/'Cargo.lock').read_bytes()==(R/'tools/project/Cargo.lock').read_bytes()
print('PASS tools and equal-content path layouts ready',flush=True)
