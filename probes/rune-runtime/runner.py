"""Standing suite controller; workers have bounded phases after lock admission."""
import argparse,hashlib,json,os,pathlib,signal,subprocess,sys,time
from jobs import Jobs,LOCK,stop_registered
P=pathlib.Path(__file__).resolve().parent
ROOT=P.parents[1]
FORK=pathlib.Path('/home/me/work/rune')
PROFILE=pathlib.Path('/tmp/rune-0169-profile')
RNX=pathlib.Path('/home/me/work/.worktrees/rnx-0169-stock')
PIN='bb8e69372353c50e271c9f115bc771c77aa6b83e'
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def git(path,*args):return subprocess.check_output(['git','-C',str(path),*args],text=True).strip()
def preflight(fork=FORK,fixtures=None):
 fixtures=P/"fixtures" if fixtures is None else pathlib.Path(fixtures)
 assert git(fork,'rev-parse','HEAD')==PIN,'wrong fork pin'
 assert not git(fork,'diff','--name-only') and not git(fork,'diff','--cached','--name-only'),'dirty fork'
 assert git(RNX,'rev-parse','HEAD')==git('/home/me/work/rnx','rev-parse','b240937'),'wrong stock source pin'
 assert not git(RNX,'status','--porcelain'),'dirty stock source'
 assert sorted(f.name for f in fixtures.glob('*.rn'))==sorted(f.name for f in (P/'fixtures').glob('*.rn')),'fixture set drift'
 for f in fixtures.glob('*.rn'):
  if f.name=='collections.rn':continue # New capability fixture, hashed separately.
  expected=subprocess.check_output(['git','-C',str(ROOT),'show','20f9806:probes/rune-base-0168/fixtures/'+f.name])
  assert f.read_bytes()==expected,'fixture drift: '+f.name
 for name in ('lua54','luajit'):assert (pathlib.Path.home()/'.local/bin'/name).is_file(),name+' unavailable'
 assert git(PROFILE,'rev-parse','HEAD')==PIN,'wrong diagnostic pin'
 patch=subprocess.check_output(['git','-C',str(PROFILE),'diff','--','crates/rune/Cargo.toml','crates/rune/src/lib.rs','crates/rune/src/compile/context.rs'])
 assert patch==(P/'registration.patch').read_bytes(),'diagnostic patch drift'
 assert (PROFILE/'crates/rune/src/registration_profile.rs').read_bytes()==(P/'registration_profile.rs').read_bytes(),'collector drift'
def build(j,out):
 for base in ('old','new','profile'):
  manifest=P/base/'Cargo.toml'
  for kind,features in [('primary',None),('counter','counter'),('allocation','allocation')]:
   if base=='profile' and kind=='counter':continue
   argv=['cargo','build','--locked','--release','--manifest-path',manifest]
   if features:argv+=['--features',features]
   j.run(argv,base+'-build-'+kind,deadline=900)
   binary=P/base/'target/release'/('rune-registration-profile' if base=='profile' else 'rune-base-'+base)
   target=binary.parent/kind;target.write_bytes(binary.read_bytes());target.chmod(0o755)
 j.run(['cargo','build','--locked','--release','--features','negative','--manifest-path',P/'profile/Cargo.toml'],'omission-control-build',deadline=900)
 b=P/'profile/target/release/rune-registration-profile';t=b.parent/'negative';t.write_bytes(b.read_bytes());t.chmod(0o755)
 j.run(['cargo','build','--locked','--release','--manifest-path',RNX/'Cargo.toml'], 'stock-build',deadline=900)
 j.run(['rustc','-O',ROOT/'probes/rustc-42/clock.rs','-o',P/'target/clock'],'clock-build',deadline=60)
 (P/'target/cached.rs').write_text('fn main(){println!("42");}\n')
 j.run(['rustc',P/'target/cached.rs','-o',P/'target/cached'],'cached-reference-build',deadline=60)
 files=list(P.glob('*.py'))+list(P.glob('*.sh'))+list(P.glob('*.patch'))+list(P.glob('*.json'))+list(P.rglob('*.rs'))+list(P.rglob('Cargo.toml'))+list(P.rglob('Cargo.lock'))+list((P/'fixtures').glob('*.rn'))
 files=[f for f in files if 'target' not in f.parts]
 binaries={base:{kind:dict(path=str(P/base/'target/release'/kind),sha256=digest(P/base/'target/release'/kind)) for kind in ('primary','allocation')+(('negative',) if base=='profile' else ())+(('counter',) if base!='profile' else ())} for base in ('old','new','profile')}
 binaries['stock']=dict(path=str(RNX/'target/release/rnx'),sha256=digest(RNX/'target/release/rnx'))
 binaries['lua']={n:dict(path=str(pathlib.Path.home()/'.local/bin'/n),sha256=digest(pathlib.Path.home()/'.local/bin'/n)) for n in ('lua54','luajit')}
 (out/'subjects.json').write_text(json.dumps(dict(binaries=binaries,environment={k:v for k,v in os.environ.items() if k in ('RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','CARGO_PROFILE_RELEASE_OPT_LEVEL','CARGO_PROFILE_RELEASE_LTO','CARGO_BUILD_TARGET','RUSTUP_TOOLCHAIN')},sources={str(f.relative_to(P)):digest(f) for f in files},rustc=subprocess.check_output(['rustc','-vV'],text=True), metadata={
   'source_pin':PIN,'stock_pin':git(RNX,'rev-parse','HEAD'),'probe_commit':git(ROOT,'rev-parse','HEAD'),'probe_status':git(ROOT,'status','--porcelain'),
   'uname':subprocess.check_output(['uname','-a'],text=True),'cpu':subprocess.check_output(['lscpu'],text=True),
   'lua_versions':{n:subprocess.check_output([str(pathlib.Path.home()/'.local/bin'/n),'-v'],stderr=subprocess.STDOUT,text=True) for n in ('lua54','luajit')},
   'features':{b:subprocess.check_output(['cargo','tree','--locked','-e','features','--manifest-path',str(P/b/'Cargo.toml')],text=True) for b in ('old','new','profile')},
   'cpu4_scaling':{f.name:f.read_text() for f in pathlib.Path('/sys/devices/system/cpu/cpu4/cpufreq').glob('scaling_*') if f.is_file()}
  }),indent=2)+'\n')
def worker(phase,out):
 j=Jobs(out/'jobs')
 def stop(sig,frame):raise RuntimeError(phase+': interrupted '+str(sig))
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 j.event('lock-acquired',phase=phase,lock=LOCK,load1=os.getloadavg()[0])
 try:
  if phase=='build':build(j,out)
  elif phase=='controls':
   from suite import controls
   controls(j,out)
  else:
   from suite import controls,measure
   (controls if phase=='controls' else measure)(j,out)
 finally:
  j.cleanup();j.event('lock-release',phase=phase,lock=LOCK,load1=os.getloadavg()[0])
def main():
 a=argparse.ArgumentParser();a.add_argument('--out',type=pathlib.Path,required=True);a.add_argument('--worker',choices=['build','controls','measurement']);args=a.parse_args()
 out=args.out.resolve()
 if args.worker:worker(args.worker,out);return
 assert not out.exists(),'output already exists; refuse before any work'
 preflight();out.mkdir(parents=True);j=Jobs(out/'controller')
 def stop(sig,frame):raise RuntimeError('controller interrupted '+str(sig))
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 (P/'target').mkdir(exist_ok=True)
 try:
  j.run([sys.executable,P/'lifecycle_controls.py'],'lifecycle-controls',deadline=1820)
  j.run([sys.executable,P/'preflight_controls.py'],'preflight-controls',deadline=30)
  for phase,deadline in [('build',1800),('controls',600),('measurement',600)]:j.locked(phase,[sys.executable,__file__,'--worker',phase,'--out',str(out)],deadline)
  j.run([sys.executable,P/'analyse.py','--out',out],'analysis',deadline=60)
  j.run([sys.executable,P/'analysis_controls.py',out],'analysis-controls',deadline=60)
  (out/'COMPLETE').write_text('PASS\n')
 finally:
  stop_registered(out/'jobs/ledger.jsonl');j.cleanup()
if __name__=='__main__':main()
