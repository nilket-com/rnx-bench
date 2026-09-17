"""Probe identity projections from the real project tool; no cache implementation."""
from pathlib import Path
import copy,hashlib,json,os,shutil,subprocess,tempfile,tomllib
B=Path(__file__).resolve().parents[2];R=B.parent/'rnx';O=B/'results/assembly-identity-0061';T=R/'tools/project/target/release/rnx-project'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_'))};rows={}
def digest(v):return hashlib.sha256(v if isinstance(v,bytes) else json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def invoke(args,**kwargs):return subprocess.run(list(map(str,args)),env=ENV,capture_output=True,text=True,timeout=120,**kwargs)
with tempfile.TemporaryDirectory(prefix='rnx-assembly-key-') as tmp:
 root=Path(tmp);n=root/'native';(n/'runtime/src').mkdir(parents=True);(n/'adapter/src').mkdir(parents=True)
 (n/'runtime/Cargo.toml').write_text('[package]\nname="rnx"\nversion="0.0.0"\nedition="2024"\n[features]\nproject-sources=[]\n')
 (n/'runtime/src/lib.rs').write_text('pub struct Extensions(Vec<fn()->String>); impl Extensions { pub fn none()->Self {Self(vec![])} pub fn with(mut self,_:&str,b:fn()->String)->Self {self.0.push(b);self} } pub fn main_with(e:Extensions)->Result<(),Box<dyn std::error::Error>> {for b in e.0 {println!("{}",b());} Ok(())}\n')
 (n/'adapter/Cargo.toml').write_text('[package]\nname="probe-adapter"\nversion="0.0.0"\nedition="2024"\n')
 (n/'adapter/src/lib.rs').write_text('pub fn build()->String {"constant 42".into()}\n')
 for cmd in [['git','init','--quiet',n],['git','-C',n,'add','.']]:assert invoke(cmd).returncode==0
 def measure(name,native=n,relative=False,entry='pub fn main(_) {42}\n',alias='probe',build=True,config=None):
  app=root/name;app.mkdir();(app/'main.rn').write_text(entry)
  if config:(app/'.cargo').mkdir();(app/'.cargo/config.toml').write_text(config)
  locate=lambda p:os.path.relpath(p,app) if relative else str(p)
  (app/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath='+json.dumps(locate(native/'runtime'))+'\n[native.'+alias+']\npath='+json.dumps(locate(native/'adapter'))+'\npackage="probe-adapter"\nbuilder="build"\nhook="plain"\n')
  d=O/name;d.mkdir(exist_ok=True)
  for mode in ['lock']+(['build'] if build else []):
   p=invoke([T,mode,'--manifest',app/'rnx.toml','--offline']);(d/(mode+'.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,(name,mode,p.stderr)
  lock=json.loads((app/'rnx.lock').read_text());stage=app/'.rnx/assembly';cargo=tomllib.loads((stage/'Cargo.toml').read_text());main=(stage/'src/main.rs').read_text();inv=lock['inputs']['native'];trees={t['root']:t['sha256'] for t in inv['trees']}
  # This is a diagnostic candidate, deliberately not a production cache key.
  # Retain dependency associations and all external candidates with absence.
  # Map native roots to content tokens, project ancestors to positional roles.
  roots=sorted(trees,key=len,reverse=True)
  def normal(value):
   if isinstance(value,str):
    for p in roots:value=value.replace(p,'@native:'+trees[p])
    value=value.replace(str(app),'@application')
    return value
   if isinstance(value,list):return [normal(x) for x in value]
   if isinstance(value,dict):return {k:normal(v) for k,v in value.items()}
   return value
  normalized=copy.deepcopy(cargo)
  for dep in normalized['dependencies'].values():
   canonical=str(Path(dep['path']).resolve());assert canonical in trees,(canonical,trees)
   dep['path']='@native:'+trees[canonical]
  # Exclude only roots/path names from tree content: the exact tree fingerprint
  # is produced by rnx-project, not a Python recreation of its byte encoding.
  native_inventory={'platform':inv['platform'],'packages':sorted(normal(inv['packages']),key=lambda x:json.dumps(x,sort_keys=True)),'trees':sorted(trees.values()),'external':sorted(normal(inv['external']),key=lambda x:json.dumps(x,sort_keys=True))}
  assembly={k:v for k,v in lock['assembly'].items() if k not in ['manifest_sha256','main_sha256']}
  candidate={'probe_format':1,'wrapper':normalized,'main':main,'assembly':assembly,'native':native_inventory}
  # A location-preserving control still excludes application sources, but pins
  # native roots and external search candidates instead of claiming relocation.
  located={'probe_format':1,'wrapper':cargo,'main':main,'assembly':assembly,'native':inv}
  # Generated Cargo manifest can contain lexical project/../native paths.
  canonical=copy.deepcopy(cargo)
  for dep in canonical['dependencies'].values():dep['path']=str(Path(dep['path']).resolve())
  # Application-local absent Cargo candidates differ only by app prefix here.
  def app_only(value):
   if isinstance(value,str):return value.replace(str(app),'@application')
   if isinstance(value,list):return [app_only(x) for x in value]
   if isinstance(value,dict):return {k:app_only(v) for k,v in value.items()}
   return value
  located['wrapper']=canonical;located['native']=app_only(inv)
  located['native']['external']=sorted(located['native']['external'],key=lambda x:json.dumps(x,sort_keys=True))
  output=None;binary=None
  if build:
   receipt=json.loads((app/'.rnx/receipt.json').read_text());exe=app/'.rnx/artifacts'/receipt['executable_sha256'];p=invoke([exe,'eval','42']);assert p.returncode==0 and not p.stderr,p;output=p.stdout;binary=digest(exe.read_bytes())
  for src,dst in [(app/'rnx.toml','rnx.toml'),(app/'rnx.lock','rnx.lock'),(app/'rnx.Cargo.lock','rnx.Cargo.lock'),(stage/'Cargo.toml','Cargo.toml'),(stage/'src/main.rs','main.rs')]:shutil.copyfile(src,d/dst)
  (d/'candidate.json').write_text(json.dumps(candidate,indent=2)+'\n');(d/'located.json').write_text(json.dumps(located,indent=2)+'\n')
  for label in ['runtime','adapter']:
   shutil.copytree(native/label,d/label,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git','target'))
  row={'lock':digest((app/'rnx.lock').read_bytes()),'raw_wrapper':digest((stage/'Cargo.toml').read_bytes()),'main':digest(main.encode()),'cargo_lock':digest((app/'rnx.Cargo.lock').read_bytes()),'candidate':digest(candidate),'located':digest(located),'output':output,'binary':binary};rows[name]=row;print(name,json.dumps(row),flush=True);return row
 a=measure('same-root-a');b=measure('same-root-b',entry='pub fn main(_) {99}\n');c=measure('relative-root',relative=True)
 assert a['lock']!=b['lock'] and a['raw_wrapper']==b['raw_wrapper'] and a['candidate']==b['candidate'] and a['located']==b['located']
 assert a['raw_wrapper']!=c['raw_wrapper'] and a['candidate']==c['candidate'] and a['located']==c['located']
 moved=root/'moved';shutil.copytree(n,moved);d=measure('relocated-constant',native=moved)
 # Additional absent ancestor candidates under relocated native roots are mapped
 # through the fixture's two native root roles, while their parent is still a
 # concrete path. Preserve this failed naive projection if it differs.
 raw_d=copy.deepcopy(json.loads((O/'relocated-constant/candidate.json').read_text()))
 def move_parent(v):
  if isinstance(v,str):return v.replace(str(moved),str(n))
  if isinstance(v,list):return [move_parent(x) for x in v]
  if isinstance(v,dict):return {k:move_parent(x) for k,x in v.items()}
  return v
 adjusted=move_parent(raw_d);adjusted['native']['external']=sorted(adjusted['native']['external'],key=lambda x:json.dumps(x,sort_keys=True))
 (O/'relocated-constant/candidate-with-parent-role.json').write_text(json.dumps(adjusted,indent=2)+'\n')
 assert digest(adjusted)==a['candidate'];assert d['located']!=a['located'];assert a['output']==d['output']
 # Native directory is an observable compile-time input even without build.rs.
 for tree in [n,moved]:(tree/'adapter/src/lib.rs').write_text('pub fn build()->String {env!("CARGO_MANIFEST_DIR").into()}\n')
 x=measure('path-sensitive-a');y=measure('path-sensitive-b',native=moved)
 adjusted=move_parent(json.loads((O/'path-sensitive-b/candidate.json').read_text()));adjusted['native']['external']=sorted(adjusted['native']['external'],key=lambda x:json.dumps(x,sort_keys=True))
 (O/'path-sensitive-b/candidate-with-parent-role.json').write_text(json.dumps(adjusted,indent=2)+'\n')
 assert x['candidate']==digest(adjusted) and x['output']!=y['output'] and x['located']!=y['located']
 # Same native roots can observe generated build location through OUT_DIR.
 (n/'adapter/build.rs').write_text('fn main(){println!("cargo:rustc-env=BUILD_ORIGIN={}",std::env::var("OUT_DIR").unwrap());}\n');(n/'adapter/src/lib.rs').write_text('pub fn build()->String {env!("BUILD_ORIGIN").into()}\n');assert invoke(['git','-C',n,'add','.']).returncode==0
 x=measure('out-dir-a');y=measure('out-dir-b')
 assert x['candidate']==y['candidate'] and x['located']==y['located'] and x['output']!=y['output']
 # Positive key invalidation controls, without pretending alternate toolchains
 # were executed. Mutations are actual tool inputs followed by actual lock.
 z=measure('alias-change',alias='other',build=False);assert z['candidate']!=x['candidate']
 (n/'adapter/src/lib.rs').write_text('pub fn build()->String {"changed".into()}\n');z=measure('content-change',build=False);assert z['candidate']!=x['candidate'] and z['cargo_lock']==x['cargo_lock']
 z2=measure('config-change',build=False,config='[net]\noffline=true\n');assert z2['candidate']!=z['candidate']
(O/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
(O/'conditions.json').write_text(json.dumps({'tool_sha256':digest(T.read_bytes()),'rnx_head':subprocess.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip(),'platform':os.uname()._asdict() if hasattr(os.uname(),'_asdict') else list(os.uname()),'python':subprocess.check_output(['python3','--version'],text=True),'scope':'ordinary project CLI with tiny API-compatible runtime; probes identities/build-time path observability, not Rune evaluation; no production cache'},indent=2)+'\n')
print('PASS: project separation, lexical paths, relocation, two counterexamples, invalidation controls',flush=True)
