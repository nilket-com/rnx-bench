"""Real private Identity module, actual Cargo/native snapshots; no Python key copy."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,tempfile
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/cache-identity-0061';T=H/'target/tool/target/release/rnx-cache-identity-probe'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_'))};rows={}
def sha(b):return hashlib.sha256(b).hexdigest()
def call(args,env,cwd=None):
 p=subprocess.run(list(map(str,args)),env=env,cwd=cwd,capture_output=True,text=True,timeout=90);assert p.returncode==0,(args,p.stdout,p.stderr);return p
oldmask=os.umask(0o077)
try:
 with tempfile.TemporaryDirectory(prefix='rnx-cache-identity-') as tmp:
  root=Path(tmp);cache=root/'cache';cache.mkdir();home=root/'cargo';home.mkdir();env=dict(ENV,CARGO_HOME=str(home));n=root/'native'
  for name in ['runtime','adapter','helper']:(n/name/'src').mkdir(parents=True)
  (n/'runtime/Cargo.toml').write_text('[package]\nname="rnx"\nversion="0.0.0"\nedition="2024"\n[features]\nproject-sources=[]\n')
  (n/'runtime/src/lib.rs').write_text('pub struct Extensions(Vec<fn()->String>);impl Extensions{pub fn none()->Self{Self(vec![])}pub fn with(mut self,_:&str,b:fn()->String)->Self{self.0.push(b);self}pub fn with_lifecycle(self,n:&str,b:fn()->String)->Self{self.with(n,b)}}pub fn main_with(e:Extensions)->Result<(),Box<dyn std::error::Error>>{for b in e.0{println!("{}",b());}Ok(())}\n')
  (n/'adapter/Cargo.toml').write_text('[package]\nname="identity-adapter"\nversion="0.0.0"\nedition="2024"\n')
  (n/'adapter/src/lib.rs').write_text('pub fn build()->String{"value 42".into()} pub fn alternate()->String{"other 42".into()}\n')
  (n/'helper/Cargo.toml').write_text('[package]\nname="identity-helper"\nversion="0.0.0"\nedition="2024"\n');(n/'helper/src/lib.rs').write_text('pub fn value()->u64{7}\n')
  call(['git','init','--quiet',n],env);call(['git','-C',n,'add','.'],env)
  mounted=root/'mounted';mounted.mkdir();(mounted/'rnx.toml').write_text('format=1\n[source]\nroot="."\n');(mounted/'mod.rn').write_text('pub fn value(){7}\n')
  toolchain=call(['rustup','show','active-toolchain'],env).stdout.split()[0]
  def case(label,native=n,relative=False,script='42',mount=None,alias='probe',builder='build',hook='plain',selected=None,cache_root=cache,cargo_home=home,cache_spelling=None,compile=False):
   app=root/label;app.mkdir();(app/'main.rn').write_text('pub fn main(_){'+script+'}\n')
   locate=lambda p:os.path.relpath(p,app) if relative else str(p)
   declaration='format=1\n[application]\nentry="main.rn"\n[runtime]\npath='+json.dumps(locate(native/'runtime'))+'\n[native.'+alias+']\npath='+json.dumps(locate(native/'adapter'))+'\npackage="identity-adapter"\nbuilder='+json.dumps(builder)+'\nhook='+json.dumps(hook)+'\n'
   if mount:declaration+='\n[sources.'+mount+']\npath='+json.dumps(str(mounted))+'\n'
   (app/'rnx.toml').write_text(declaration)
   effective=dict(env,CARGO_HOME=str(cargo_home))
   if selected:effective['RUSTUP_TOOLCHAIN']=selected
   stage=cache_root/'resolve'/label/'assembly';stage.mkdir(parents=True)
   call([T,'prepare',cache_root,stage,app],effective)
   meta=call(['cargo','metadata','--offline','--format-version','1','--manifest-path',stage/'Cargo.toml'],effective,stage).stdout
   d=O/label;d.mkdir(exist_ok=True);(d/'metadata.json').write_text(meta)
   rustc=call(['rustc','-Vv'],effective,stage).stdout;cargo=call(['cargo','-V'],effective,stage).stdout
   context={'cache_root':str(cache_spelling or cache_root),'cargo_home':str(cargo_home),'rustup_home':None,'rustup_toolchain':selected,'rustc':rustc,'cargo':cargo,'target':next(x[6:] for x in rustc.splitlines() if x.startswith('host: ')),'profile':'release','features':['project-sources']}
   (d/'context.json').write_text(json.dumps(context,indent=2)+'\n')
   result=json.loads(call([T,'identity',cache_root,stage,app,d/'metadata.json',cargo_home,d/'context.json',stage/'Cargo.lock'],effective).stdout)
   encoded=result['canonical'].encode();assert sha(encoded)==result['key'];doc=json.loads(encoded)
   assert str(app) not in result['canonical'] and str(stage) not in result['canonical'] and str(mounted) not in result['canonical']
   assert doc['manifest']==(stage/'Cargo.toml').read_text() and doc['main']==(stage/'src/main.rs').read_text()
   shuffled=json.loads(call([T,'identity-shuffled',cache_root,stage,app,d/'metadata.json',cargo_home,d/'context.json',stage/'Cargo.lock'],effective).stdout);assert shuffled==result
   (d/'identity.json').write_bytes(encoded);(d/'identity.pretty.json').write_text(json.dumps(doc,indent=2)+'\n')
   output=None;artifact=None
   if compile:
    p=call(['cargo','build','--offline','--locked','--release','--manifest-path',stage/'Cargo.toml','--target-dir',cache_root/'fixture-targets'/label],effective,stage);(d/'build.log').write_text(p.stdout+p.stderr)
    executable=cache_root/'fixture-targets'/label/'release/rnx-project-app';output=call([executable],effective,app).stdout;artifact=sha(executable.read_bytes())
   for p,name in [(app/'rnx.toml','rnx.toml'),(app/'main.rn','main.rn'),(stage/'Cargo.toml','Cargo.toml'),(stage/'Cargo.lock','Cargo.lock'),(stage/'src/main.rs','main.rs')]:shutil.copyfile(p,d/name)
   for name in ['runtime','adapter','helper']:shutil.copytree(native/name,d/name,dirs_exist_ok=True)
   row={'key':result['key'],'manifest_sha256':sha((stage/'Cargo.toml').read_bytes()),'main_sha256':sha((stage/'src/main.rs').read_bytes()),'cargo_lock_sha256':sha((stage/'Cargo.lock').read_bytes()),'output':output,'artifact_sha256':artifact};rows[label]=row;print(label,row['key'],flush=True);return row
  base=case('baseline',compile=True)
  for label,kwargs in [('different-script',{'script':'99'}),('mapped-package',{'mount':'dep'}),('renamed-mount',{'mount':'different'}),('relative-native-paths',{'relative':True})]:assert case(label,**kwargs)['key']==base['key']
  (mounted/'mod.rn').write_text('pub fn value(){999}\n');assert case('edited-mapped-source',mount='dep')['key']==base['key']
  link=root/'cache-link';link.symlink_to(cache,target_is_directory=True);assert case('symlink-cache-selection',cache_spelling=link)['key']==base['key']
  moved=root/'moved-native';shutil.copytree(n,moved);assert case('relocated-native',native=moved,compile=True)['key']!=base['key']
  for label,kwargs in [('registration-name',{'alias':'renamed'}),('builder-path',{'builder':'alternate'}),('lifecycle-hook',{'hook':'lifecycle'})]:assert case(label,compile=True,**kwargs)['key']!=base['key']
  source=n/'adapter/src/lib.rs';original=source.read_bytes();source.write_bytes(original.replace(b'value 42',b'value 43'))
  changed=case('native-edit',compile=True);assert changed['key']!=base['key'] and changed['cargo_lock_sha256']==base['cargo_lock_sha256'] and changed['output']=='value 43\n';source.write_bytes(original)
  source=n/'runtime/src/lib.rs';original=source.read_bytes();source.write_bytes(original+b'// runtime edit\n');changed=case('runtime-edit');assert changed['key']!=base['key'];source.write_bytes(original)
  # Graph change comes from real metadata/lock resolution, not editing a hash.
  manifest=n/'adapter/Cargo.toml';original=manifest.read_bytes();manifest.write_bytes(original+b'\n[dependencies]\nidentity-helper={path="../helper"}\n')
  changed=case('cargo-graph',compile=True);assert changed['key']!=base['key'] and changed['cargo_lock_sha256']!=base['cargo_lock_sha256'];manifest.write_bytes(original)
  # Actual default-feature activation is an input in native manifest contents.
  manifest.write_bytes(original+b'\n[features]\ndefault=["flavour"]\nflavour=[]\n');changed=case('native-default-feature',compile=True);assert changed['key']!=base['key'];manifest.write_bytes(original)
  explicit=case('explicit-toolchain',selected=toolchain);assert explicit['key']!=base['key']
  (home/'config.toml').write_text('[net]\noffline=true\n');assert case('new-cargo-config')['key']!=base['key'];(home/'config.toml').unlink()
  other_cache=root/'other-cache';other_cache.mkdir();assert case('different-cache-root',cache_root=other_cache)['key']!=base['key']
  other_home=root/'other-cargo';other_home.mkdir();assert case('different-cargo-home',cargo_home=other_home)['key']!=base['key']
  assert case('restored-baseline')['key']==base['key']
  (O/'results.json').write_text(json.dumps(rows,indent=2)+'\n');(O/'conditions.json').write_text(json.dumps({'prototype_sha256':sha(T.read_bytes()),'rnx_head':call(['git','-C',R,'rev-parse','HEAD'],env).stdout.strip(),'source_patch':'source.patch','installed_toolchain':toolchain,'scope':'real private key and inventories; tiny API-compatible runtime; no cache product, target/profile feature-string counterfactuals are unit tests only'},indent=2)+'\n')
finally:os.umask(oldmask)
print('PASS',len(rows),'real identity cases',flush=True)
