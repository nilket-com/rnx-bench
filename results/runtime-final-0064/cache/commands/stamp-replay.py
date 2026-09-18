"""Product receipt/flag/read-count and failure gates on a private assembled app."""
import hashlib,json,os,pathlib,shutil,signal,subprocess,tempfile,time
B=pathlib.Path('/home/me/work/rnx-bench');R=B.parent/'rnx';O=pathlib.Path('/home/me/work/rnx-bench/results/runtime-final-0064/cache/commands');T=R/'tools/project/target/debug/rnx-project'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_'))};results={}
with tempfile.TemporaryDirectory(prefix='rnx-stamp-contract-') as tmp:
 root=pathlib.Path(tmp);app=root/'app';native=root/'runtime';app.mkdir();(native/'src').mkdir(parents=True)
 (native/'Cargo.toml').write_text('[package]\nname="rnx"\nversion="0.0.0"\nedition="2024"\n[features]\nproject-sources=[]\n')
 (native/'src/lib.rs').write_text('pub struct Extensions; impl Extensions {pub fn none()->Self{Self}} pub fn main_with(_:Extensions)->Result<(),Box<dyn std::error::Error>> {let a=std::env::args().collect::<Vec<_>>(); if a[1]=="project-source-version" {println!("{}", r#"{"format":1}"#);} else {println!("RAN:{}",a.last().unwrap());} Ok(())}')
 for cmd in [['git','init','--quiet',native],['git','-C',native,'add','.']]:subprocess.run(list(map(str,cmd)),check=True)
 manifest=app/'rnx.toml';manifest.write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath="../runtime"\n');entry=app/'main.rn';entry.write_text('pub fn main(_) {42}\n')
 receipt=app/'.rnx/receipt.json';readlog=root/'reads';artifact=None
 def cmd(op='run',args=()):return [(str('/home/me/work/rnx-bench/probes/cache-commands/target/legacy-tool') if op=="lock" else str(T)),op,'--manifest',str(manifest),*args]
 def run(op='run',args=('--','sentinel'),ok=True,extra=None):
  readlog.unlink(missing_ok=True);env=dict(ENV,**(extra or {}))
  if artifact:env.update(RNX_PROJECT_COUNT_ARTIFACT=str(artifact),RNX_PROJECT_READ_LOG=str(readlog))
  p=subprocess.run(cmd(op,args),env=env,capture_output=True,text=True,timeout=60)
  assert (p.returncode==0)==ok,(op,args,p.returncode,p.stdout,p.stderr)
  if not ok:assert not p.stdout
  count=sum(map(int,readlog.read_text().splitlines())) if readlog.exists() else 0
  return p,count
 run('lock',('--offline',));run('build',('--offline',));r=json.loads(receipt.read_text());assert r['format']==2
 artifact=app/'.rnx/artifacts'/r['executable_sha256'];size=artifact.stat().st_size;original=artifact.read_bytes()
 assert run()[1]==0;assert run(args=('--verify','--','sentinel'))[1]==size;assert run()[1]==0
 # Flag can precede the manifest and after -- is an ordinary script argument.
 p=subprocess.run([T,'run','--verify','--manifest',manifest,'--','sentinel'],env=ENV,capture_output=True,text=True);assert p.returncode==0 and p.stdout=='RAN:sentinel\n'
 assert run(args=('--','--verify'))[0].stdout=='RAN:--verify\n'
 run(args=('--verify','--verify'),ok=False);run('lock',('--verify',),False);run('build',('--verify',),False)
 results['default_zero_verify_full_and_flags']=True
 legacy=dict(r);legacy['format']=1;legacy.pop('stamp');receipt.write_text(json.dumps(legacy));assert run()[1]==size;assert json.loads(receipt.read_text())['format']==2;assert run()[1]==0
 results['legacy_one_full_read_then_fast']=True
 good=receipt.read_bytes()
 for change in [dict(r,format=99),dict(r,stamp=None),dict(r,extra=True),dict(r,lock_sha256='0'*64)]:
  receipt.write_text(json.dumps(change));run(ok=False)
 receipt.unlink();run(ok=False);receipt.write_bytes(good)
 results['generated_bad_or_missing_receipt_refused']=True
 st=artifact.stat();os.utime(artifact,ns=(st.st_atime_ns,st.st_mtime_ns+1_000_000_000));assert run()[1]==size;assert run()[1]==0
 for changed in [False,True]:
  held=artifact.open('rb');old=artifact.stat();replacement=root/'replacement';replacement.write_bytes((bytes([original[0]^1])+original[1:]) if changed else original);replacement.chmod(old.st_mode);os.utime(replacement,ns=(old.st_atime_ns,old.st_mtime_ns));replacement.replace(artifact);assert artifact.stat().st_ino!=old.st_ino
  p,count=run(ok=not changed);assert count==size
  if changed:assert 'hash mismatch' in p.stderr;artifact.write_bytes(original);run()
  held.close()
 results['touch_and_identical_replacement_refresh_different_replacement_refuses']=True
 source=entry.read_bytes();st=entry.stat();entry.write_bytes(source.replace(b'42',b'43'));os.utime(entry,ns=(st.st_atime_ns,st.st_mtime_ns));p,count=run(ok=False);assert 'changed' in p.stderr and count==0;entry.write_bytes(source)
 results['same_size_restored_source_time_still_refused']=True
 # Full verification gets a current stamp but publication failure cannot replace receipt.
 old=receipt.read_bytes();st=artifact.stat();os.utime(artifact,ns=(st.st_atime_ns,st.st_mtime_ns+1_000_000_000));run(ok=False,extra={'RNX_PROJECT_FAIL':'before-receipt-refresh'});assert receipt.read_bytes()==old
 def pause(name):
  marker=root/'paused';marker.unlink(missing_ok=True);env=dict(ENV,RNX_PROJECT_PAUSE=name,RNX_PROJECT_PAUSE_FILE=str(marker));p=subprocess.Popen(cmd(args=('--verify','--','sentinel')),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  deadline=time.monotonic()+15
  try:
   while not marker.exists():
    assert p.poll() is None,p.communicate();assert time.monotonic()<deadline;time.sleep(.01)
   return p,marker
  except BaseException:
   if p.poll() is None:p.kill()
   p.communicate();marker.unlink(missing_ok=True);raise
 p,marker=pause('before-receipt-refresh')
 try:
  p.send_signal(signal.SIGINT);out,err=p.communicate(timeout=5);assert p.returncode==130 and not out;assert receipt.read_bytes()==old
 finally:
  if p.poll() is None:p.kill();p.communicate()
  marker.unlink(missing_ok=True)
 run();old=receipt.read_bytes();p,marker=pause('artifact-hashed')
 try:
  artifact.write_bytes(original+b'x');marker.unlink();out,err=p.communicate(timeout=10);assert p.returncode!=0 and not out and 'changed' in err;assert receipt.read_bytes()==old
 finally:
  if p.poll() is None:p.kill();p.communicate()
  marker.unlink(missing_ok=True);artifact.write_bytes(original)
 run();results['refresh_failure_interrupt_and_hash_to_stamp_change']=True
 # Override establishment/stale receipt has no Cargo/build requirement.
 override=root/'override';shutil.copy2(artifact,override);artifact=app/'../override';size=artifact.stat().st_size
 manifest.write_text('format=1\n[application]\nentry="main.rn"\n[executable]\npath="../override"\n');run('lock',('--offline',));assert run()[1]==size;assert run()[1]==0;assert run(args=('--verify','--','sentinel'))[1]==size
 receipt.unlink();assert run()[1]==size;assert run()[1]==0
 receipt.write_text('{broken');run(ok=False);receipt.unlink();run();old=json.loads(receipt.read_text());old['lock_sha256']='0'*64;receipt.write_text(json.dumps(old));assert run()[1]==size;assert run()[1]==0
 results['override_establish_missing_stale_and_verify']=True
(O/'contracts.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS',len(results),'contract groups',flush=True)
