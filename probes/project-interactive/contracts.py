"""Actual CLI orchestration on an API-compatible argv-reporting fixture, not Rune."""
import json,os,pathlib,subprocess,tempfile,shutil
B=pathlib.Path(__file__).resolve().parents[2]; R=B.parent/'rnx'; O=B/'results/project-interactive-0060'; T=R/'tools/project/target/debug/rnx-project'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_'))}; results={}
with tempfile.TemporaryDirectory(prefix='rnx-0060-contract-') as tmp:
 root=pathlib.Path(tmp); app=root/'app'; native=root/'runtime'; app.mkdir();(native/'src').mkdir(parents=True)
 (native/'Cargo.toml').write_text('[package]\nname="rnx"\nversion="0.0.0"\nedition="2024"\n[features]\nproject-sources=[]\n')
 (native/'src/lib.rs').write_text('pub struct Extensions; impl Extensions {pub fn none()->Self{Self}} pub fn main_with(_:Extensions)->Result<(),Box<dyn std::error::Error>> { for a in std::env::args_os().skip(1) {println!("{:?}",a);} Ok(())}')
 for cmd in [['git','init','--quiet',native],['git','-C',native,'add','.']]:subprocess.run(list(map(str,cmd)),check=True)
 manifest=app/'rnx.toml';manifest.write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath="../runtime"\n');entry=app/'main.rn';entry.write_text('pub fn main(_) {42}\n')
 receipt=app/'.rnx/receipt.json';reads=root/'reads';artifact=None
 def run(mode,args=(),ok=True,extra=None):
  reads.unlink(missing_ok=True);env=dict(ENV,**(extra or {}))
  if artifact:env.update(RNX_PROJECT_COUNT_ARTIFACT=str(artifact),RNX_PROJECT_READ_LOG=str(reads))
  p=subprocess.run([T,mode,'--manifest',manifest,*args],env=env,capture_output=True,text=True,timeout=60)
  assert (p.returncode==0)==ok,(mode,args,p.stdout,p.stderr)
  if not ok:assert not p.stdout
  return p,sum(map(int,reads.read_text().splitlines())) if reads.exists() else 0
 run('lock',['--offline']);run('build',['--offline']);r=json.loads(receipt.read_text());artifact=app/'.rnx/artifacts'/r['executable_sha256'];size=artifact.stat().st_size
 for form in ['generated','override']:
  if form=='override':
   override=root/'override';shutil.copy2(artifact,override);artifact=app/'../override';manifest.write_text('format=1\n[application]\nentry="main.rn"\n[executable]\npath="../override"\n');run('lock',['--offline']);assert run('session')[1]==size
  for mode,tail in [('session',[]),('eval',['--','hello\n🦀'])]:
   assert run(mode,tail)[1]==0
   assert run(mode,['--verify',*tail])[1]==size
   p=subprocess.run([T,mode,'--verify','--manifest',manifest,*tail],env=ENV,capture_output=True,text=True);assert p.returncode==0,p.stderr
   old=json.loads(receipt.read_text());old['format']=1;old.pop('stamp');receipt.write_text(json.dumps(old));assert run(mode,tail)[1]==size;assert run(mode,tail)[1]==0
   good=receipt.read_bytes();receipt.write_text('{broken');run(mode,tail,False);receipt.write_bytes(good)
   receipt.unlink()
   if form=='generated':run(mode,tail,False);receipt.write_bytes(good)
   else:assert run(mode,tail)[1]==size
   st=artifact.stat();os.utime(artifact,ns=(st.st_atime_ns,st.st_mtime_ns+1_000_000_000));assert run(mode,tail)[1]==size;assert run(mode,tail)[1]==0
   good=receipt.read_bytes();bad=json.loads(good);bad['lock_sha256']='0'*64;receipt.write_text(json.dumps(bad))
   if form=='generated':run(mode,tail,False);receipt.write_bytes(good)
   else:assert run(mode,tail)[1]==size
   raw=entry.read_bytes();st=entry.stat();entry.write_bytes(raw.replace(b'42',b'43'));os.utime(entry,ns=(st.st_atime_ns,st.st_mtime_ns));p,n=run(mode,tail,False);assert n==0 and 'changed' in p.stderr;entry.write_bytes(raw)
   original=artifact.read_bytes();st=artifact.stat();held=artifact.open('rb');replacement=root/'replacement';replacement.write_bytes(bytes([original[0]^1])+original[1:]);replacement.chmod(st.st_mode);os.utime(replacement,ns=(st.st_atime_ns,st.st_mtime_ns));replacement.replace(artifact);assert artifact.stat().st_ino!=st.st_ino
   p,n=run(mode,tail,False);assert n==size and 'hash mismatch' in p.stderr;held.close();artifact.write_bytes(original);run(mode,tail)
  results[form+'_verification']=True
 p,_=run('session',['--color=never','--no-splash']);assert p.stdout=='"--color=never"\n"--no-splash"\n"repl"\n',p.stdout
 for src in ['', '-42','--verify','first\nsecond','🦀']:
  p,_=run('eval',['--color=always','--',src]);assert p.stdout.splitlines()[:2]==['"--color=always"','"eval"'];assert json.loads(p.stdout.splitlines()[2])==src
 p,_=run('run',['--','--verify']);assert p.stdout.splitlines()[-1]=='"--verify"'
 # Neither executable lookup nor project creation may precede syntax refusal.
 bad={'session':[['--'],['extra'],['--offline'],['--verify','--verify'],['--no-splash','--no-splash'],['--color=no'],['--color=never','--color=always']], 'eval':[[],['42'],['--'],['--','a','b'],['--no-splash','--','1'],['--offline','--','1'],['--verify','--verify','--','1'],['--color=no','--','1']]}
 for mode,cases in bad.items():
  for args in cases:
   p=subprocess.run([T,mode,'--manifest',root/'absent',*args],env=ENV,capture_output=True,text=True);assert p.returncode!=0 and not p.stdout and 'No such file' not in p.stderr,(mode,args,p.stderr)
 results['argv_and_early_refusals']=True
 traps=root/'traps';traps.mkdir();marker=root/'compiler-invoked'
 for name in ['cargo','rustc']:
  f=traps/name;f.write_text('#!/bin/sh\necho invoked > '+str(marker)+'\nexit 91\n');f.chmod(0o755)
 for mode,tail in [('session',[]),('eval',['--','1'])]:run(mode,tail,extra={'PATH':str(traps)+os.pathsep+ENV['PATH']})
 assert not marker.exists();results['no_compiler_launch']=True
(O/'contracts.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS',results)
