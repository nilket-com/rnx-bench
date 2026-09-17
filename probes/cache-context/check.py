"""Gate 1 only: real generation/inventory, stable context and retained outputs."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,tempfile,tomllib
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/cache-context-0061';T=H/'target/tool/target/release/rnx-cache-context-probe'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_'))};results={};commands=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def encode(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def private(p):p.mkdir(parents=True,exist_ok=True);p.chmod(0o700)
def run(args,env=ENV,cwd=None,ok=True,trace=None):
 args=list(map(str,args));commands.append({'argv':args,'cwd':str(cwd) if cwd else None,'expect_success':ok})
 if trace:args=['strace','-f','-e','trace=openat,readlink,statx,newfstatat','-o',str(O/(trace+'.strace')),*args]
 p=subprocess.run(args,cwd=cwd,env=env,capture_output=True,text=True,timeout=90)
 assert (p.returncode==0)==ok,(args,p.returncode,p.stdout,p.stderr)
 return p
oldmask=os.umask(0o077)
try:
 with tempfile.TemporaryDirectory(prefix='rnx-cache-context-') as tmp:
  top=Path(tmp);cache=top/'disk/cache';private(cache);alias=top/'cache-link';alias.symlink_to(cache,target_is_directory=True)
  home=top/'cargo-home';private(home);env=dict(ENV,CARGO_HOME=str(home))
  # Pin an already installed toolchain through the actual cache search chain.
  toolchain=run(['rustup','show','active-toolchain']).stdout.split()[0]
  (cache/'rust-toolchain.toml').write_text('[toolchain]\nchannel='+json.dumps(toolchain)+'\n')
  private(cache/'.cargo');(cache/'.cargo/config.toml').write_text('[net]\noffline=true\n')
  # Cargo home has a separately recorded allowed input.
  (home/'config.toml').write_text('[term]\ncolor="never"\n')
  n=top/'native';private(n/'runtime/src');private(n/'adapter/src')
  (n/'runtime/Cargo.toml').write_text('[package]\nname="rnx"\nversion="0.0.0"\nedition="2024"\n[features]\nproject-sources=[]\n')
  (n/'runtime/src/lib.rs').write_text('pub struct Extensions(Vec<fn()->String>);impl Extensions{pub fn none()->Self{Self(vec![])}pub fn with(mut self,_:&str,b:fn()->String)->Self{self.0.push(b);self}}pub fn main_with(e:Extensions)->Result<(),Box<dyn std::error::Error>>{for b in e.0{println!("{}",b());}Ok(())}\n')
  (n/'adapter/Cargo.toml').write_text('[package]\nname="context-adapter"\nversion="0.0.0"\nedition="2024"\n')
  (n/'adapter/build.rs').write_text('fn main(){let p=std::path::PathBuf::from(std::env::var("OUT_DIR").unwrap()).join("retained.txt");std::fs::write(&p,"cache-owned retained value").unwrap();println!("cargo:rustc-env=RETAINED_PATH={}",p.display());}\n')
  (n/'adapter/src/lib.rs').write_text('pub fn build()->String{let p=env!("RETAINED_PATH");format!("{}\\n{}\\n{}",env!("CARGO_MANIFEST_DIR"),p,std::fs::read_to_string(p).unwrap())}\n')
  run(['git','init','--quiet',n]);run(['git','-C',n,'add','.'])
  projects=[]
  for label,value in [('a',42),('b',99)]:
   p=top/label;private(p);(p/'main.rn').write_text(f'pub fn main(_){{{value}}}\n');(p/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath="../native/runtime"\n[native.probe]\npath="../native/adapter"\npackage="context-adapter"\nbuilder="build"\nhook="plain"\n');projects.append(p)
  a,b=projects
  for parent in ['resolve','entries']:private(cache/parent)
  scratch=cache/'resolve/one/assembly';private(scratch)
  def guard(stage,project=a,ok=True):return run([T,'guard',alias,stage,project],env=env,ok=ok)
  def prepare(stage,project):return run([T,'prepare',alias,stage,project],env=env)
  def metadata(stage,label):
   guard(stage);pre=run([T,'preflight',alias,stage,a,home],env=env);(O/(label+'.preflight.json')).write_text(pre.stdout)
   p=run(['cargo','metadata','--format-version','1','--manifest-path',stage/'Cargo.toml'],env=env,cwd=stage,trace=label)
   path=O/(label+'.metadata.json');path.write_text(p.stdout);return path
  def audit(stage,meta,project=a):
   p=run([T,'audit',alias,stage,project,meta,home],env=env);return json.loads(p.stdout)
  def versions(stage):return {cmd:run(args,env=env,cwd=stage).stdout for cmd,args in [('cargo',['cargo','-V']),('rustc',['rustc','-Vv']),('selected',['rustup','show','active-toolchain'])]}
  prepare(scratch,a);m=metadata(scratch,'resolve');inv=audit(scratch,m);v=versions(scratch)
  # Main/manifest are produced by the real generator, canonicalized in Rust.
  cargo=(scratch/'Cargo.toml').read_bytes();main=(scratch/'src/main.rs').read_bytes();lock=(scratch/'Cargo.lock').read_bytes()
  identity={'probe_format':1,'generator':'0061-context-prototype','cache_root':str(cache),'cargo_home':str(home),'wrapper':cargo.decode(),'main':main.decode(),'cargo_lock_sha256':sha(lock),'native':inv,'toolchain':v,'target':next(l[6:] for l in v['rustc'].splitlines() if l.startswith('host: ')),'profile':'release','features':['project-sources'],'selection':{'RUSTUP_HOME':env.get('RUSTUP_HOME'),'RUSTUP_TOOLCHAIN':env.get('RUSTUP_TOOLCHAIN')}}
  key=sha(encode(identity));entry=cache/'entries'/key;stage=entry/'assembly';private(stage);prepare(stage,a);(stage/'Cargo.lock').write_bytes(lock)
  assert cargo==(stage/'Cargo.toml').read_bytes() and main==(stage/'src/main.rs').read_bytes()
  final_meta=metadata(stage,'final');final_inv=audit(stage,final_meta)
  assert final_inv==inv and versions(stage)==v
  assert str(scratch) not in json.dumps(identity) and str(stage) not in json.dumps(identity) and key not in json.dumps(identity)
  results['same_context_without_recursive_key']=True
  # Prove Cargo itself reads both allowed config sources; no untraced assumption.
  for label in ['resolve','final']:
   trace=(O/(label+'.strace')).read_text()
   for file in [cache/'.cargo/config.toml',home/'config.toml']:
    assert any(str(file) in line and 'openat(' in line and '= -1' not in line for line in trace.splitlines()),(label,file)
  results['cargo_reads_cache_and_home_configuration']=True
  # Run a resolver at both positions on a deliberately uncached crate without
  # passing --offline. The observed offline error proves the allowed setting acts.
  for label,where in [('resolve',scratch),('final',stage)]:
   original=(where/'Cargo.toml').read_bytes()
   try:
    with (where/'Cargo.toml').open('a') as f:f.write('\n[dependencies.rnx_context_probe_never_published_0061]\nversion="=0.0.1"\n')
    p=run(['cargo','metadata','--format-version','1','--manifest-path',where/'Cargo.toml'],env=env,cwd=where,ok=False)
    assert 'offline' in p.stderr and 'rnx_context_probe_never_published_0061' in p.stderr;pout=O/(label+'-offline.log');pout.write_text(p.stdout+p.stderr)
   finally:(where/'Cargo.toml').write_bytes(original)
  results['offline_setting_effect_at_both_locations']=True
  # Actual cold fixture build at its final location. Nothing is moved afterwards.
  guard(stage);assert audit(stage,final_meta)==inv
  p=run(['cargo','build','--locked','--release','--manifest-path',stage/'Cargo.toml','--target-dir',entry/'target'],env=env,cwd=stage,trace='build');(O/'cargo-build.log').write_text(p.stdout+p.stderr)
  postmeta=metadata(stage,'post-build');assert audit(stage,postmeta)==inv;assert (stage/'Cargo.lock').read_bytes()==lock
  exe=entry/'target/release/rnx-project-app';outputs=[]
  for project in projects:
   out=run([exe],env=env,cwd=project).stdout;outputs.append(out)
  assert outputs[0]==outputs[1];lines=outputs[0].splitlines();assert lines[0]==str(n/'adapter') and lines[2]=='cache-owned retained value'
  retained=Path(lines[1]);assert retained.is_relative_to(entry/'target') and retained.read_text()=='cache-owned retained value'
  # The second consumer resolves independently, but reaches the same identity.
  scratch2=cache/'resolve/two/assembly';private(scratch2);prepare(scratch2,b);(scratch2/'Cargo.lock').write_bytes(lock);m2=metadata(scratch2,'second-project');i2=audit(scratch2,m2,b)
  assert i2==inv and (scratch2/'Cargo.toml').read_bytes()==cargo and (scratch2/'src/main.rs').read_bytes()==main and versions(scratch2)==v
  # Remove only temporary resolution workspaces; retained entry continues to work.
  shutil.rmtree(cache/'resolve');assert run([exe],env=env,cwd=b).stdout==outputs[0]
  results['two_consumers_same_native_and_retained_output']=True
  # Missing retained output is an observable failure: the lifetime claim is real.
  content=retained.read_bytes();retained.unlink()
  try:failed=run([exe],env=env,cwd=b,ok=False);assert 'No such file' in failed.stderr
  finally:retained.write_bytes(content)
  assert run([exe],env=env,cwd=a).stdout==outputs[0];results['retained_file_positive_and_missing_control']=True
  refusals=[]
  # Inject candidates AFTER pre-build audit. These are refused before any Cargo
  # call. The plan's managed-path rule begins below canonical root.
  for parent in [cache/'entries',entry,stage]:
   for name in ['Cargo.toml','.cargo/config','.cargo/config.toml','rust-toolchain','rust-toolchain.toml']:
    if parent==stage and name=='Cargo.toml':continue
    path=parent/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('unexpected')
    try:p=guard(stage,ok=False);assert str(path) in p.stderr;refusals.append({'path':str(path),'error':p.stderr})
    finally:path.unlink()
  for name in ['.cargo/config','.cargo/config.toml','rust-toolchain','rust-toolchain.toml']:
   path=a/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('unexpected')
   try:p=guard(stage,ok=False);assert str(path) in p.stderr and 'outside shared cache context' in p.stderr;refusals.append({'path':str(path),'error':p.stderr})
   finally:path.unlink()
  # Existing audited cache config modification changes identity; illegal keys refuse.
  conf=cache/'.cargo/config.toml';old=conf.read_bytes();conf.write_text('[net]\noffline=false\n');assert audit(stage,postmeta)!=inv
  conf.write_text('[build]\nrustflags=["-Copt-level=0"]\n')
  p=run([T,'audit',alias,stage,a,postmeta,home],env=env,ok=False);assert 'unsupported Cargo configuration key build' in p.stderr
  p=run([T,'preflight',alias,stage,a,home],env=env,ok=False);assert 'unsupported Cargo configuration key build' in p.stderr;conf.write_bytes(old)
  assert audit(stage,postmeta)==inv;results['audited_change_and_unsupported_config']=True
  extra=home/'config';extra.write_text('[net]\noffline=true\n')
  try:assert audit(stage,postmeta)!=inv
  finally:extra.unlink()
  assert audit(stage,postmeta)==inv;results['absent_external_candidate_becomes_present']=True
  for name in ['Cargo.toml','Cargo.lock','src/main.rs']:
   path=stage/name;original=path.read_bytes();saved=top/'saved-input';saved.write_bytes(original);path.unlink();path.symlink_to(saved)
   try:p=guard(stage,ok=False);assert 'managed input is not regular' in p.stderr
   finally:path.unlink();path.write_bytes(original)
  results['generated_input_symlinks_refused']=True

  # A managed directory symlink or special file cannot be canonicalized away.
  linked=cache/'entries/link';linked.symlink_to(entry,target_is_directory=True)
  p=guard(linked/'assembly',ok=False);assert 'private owned directory' in p.stderr;linked.unlink()
  fifo=cache/'entries/fifo';os.mkfifo(fifo);p=guard(fifo/'assembly',ok=False);assert 'private owned directory' in p.stderr;fifo.unlink()
  # Non-file candidate cannot hang or evade the managed-input check.
  fifo=entry/'rust-toolchain';os.mkfifo(fifo);p=guard(stage,ok=False);assert 'unexpected managed Cargo input' in p.stderr;fifo.unlink()
  results['user_root_symlink_allowed_managed_symlink_and_fifo_refused']=True
  results['late_candidate_refusals']=len(refusals)
  (O/'refusals.json').write_text(json.dumps(refusals,indent=2)+'\n');(O/'identity.json').write_text(json.dumps(identity,indent=2)+'\n');(O/'observations.json').write_text(json.dumps({'key':key,'outputs':outputs,'retained_path':str(retained),'artifact_sha256':sha(exe.read_bytes()),'artifact_bytes':exe.stat().st_size,'entry_regular_file_bytes':sum(x.stat().st_size for x in entry.rglob('*') if x.is_file()),'results':results},indent=2)+'\n')
  for label,where in [('runtime',n/'runtime'),('adapter',n/'adapter')]:shutil.copytree(where,O/label,dirs_exist_ok=True)
  (O/'Cargo.toml').write_bytes(cargo);(O/'main.rs').write_bytes(main);(O/'Cargo.lock').write_bytes(lock);(O/'retained.txt').write_bytes(content)
  for name,path in [('cache-config.toml',conf),('cache-toolchain.toml',cache/'rust-toolchain.toml'),('cargo-home-config.toml',home/'config.toml')]:shutil.copyfile(path,O/name)
  (O/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');(O/'conditions.json').write_text(json.dumps({'prototype_sha256':sha(T.read_bytes()),'rnx_head':run(['git','-C',R,'rev-parse','HEAD']).stdout.strip(),'strace_version':run(['strace','-V']).stdout.splitlines()[0],'env_selection':{k:env.get(k) for k in ['CARGO_HOME','RUSTUP_HOME','RUSTUP_TOOLCHAIN']},'scope':'fixture source/runtime, real generator/inventory/Cargo; no product cache/receipt/concurrency implementation'},indent=2)+'\n')
finally:os.umask(oldmask)
print('PASS',json.dumps(results),flush=True)
