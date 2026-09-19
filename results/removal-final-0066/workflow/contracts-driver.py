"""Real CLI migration, using a legacy product binary and tiny Cargo runtime."""
from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,tempfile,time
H=Path('/home/me/work/rnx-bench/probes/removal-final/target/workflow');B=Path('/home/me/work/rnx-bench');R=B.parent/'rnx';T=R/'tools/project/target/debug/rnx-project';OLD=B/'probes/native-inventory/target/stock/tools/project/target/release/rnx-project';O=B/'results/removal-final-0066/workflow'
E={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_'))};results={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def call(args,env,cwd=None,ok=True):
 p=subprocess.run(list(map(str,args)),env=env,cwd=cwd,capture_output=True,text=True,timeout=90)
 assert (p.returncode==0)==ok,(args,p.returncode,p.stdout,p.stderr)
 return p
with tempfile.TemporaryDirectory(prefix='rnx-cache-commands-') as tmp:
 root=Path(tmp);cache=root/'cache';env=dict(E,RNX_PROJECT_CACHE=str(cache));native=root/'runtime';(native/'src').mkdir(parents=True)
 (native/'Cargo.toml').write_text('[package]\nname="rnx"\nversion="0.0.0"\nedition="2024"\n[features]\nproject-sources=[]\n')
 buildlog=root/'builds';env['RNX_FIXTURE_BUILD_LOG']=str(buildlog)
 (native/'build.rs').write_text('use std::io::Write;fn main(){let p=std::env::var("RNX_FIXTURE_BUILD_LOG").unwrap();let mut f=std::fs::OpenOptions::new().create(true).append(true).open(p).unwrap();writeln!(f,"{}",std::env::var("OUT_DIR").unwrap()).unwrap();}')
 source='pub struct Extensions;impl Extensions{pub fn none()->Self{Self}}pub fn main_with(_:Extensions)->Result<(),Box<dyn std::error::Error>>{for a in std::env::args().skip(1){println!("{:?}",a);}Ok(())}'
 (native/'src/lib.rs').write_text(source)
 for cmd in [['git','init','--quiet',native],['git','-C',native,'add','.']]:call(cmd,env)
 apps=[]
 for name in ['legacy','second']:
  app=root/(name+" space'quote");app.mkdir();(app/'main.rn').write_text('pub fn main(_){42}\n');(app/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath="../runtime"\n');apps.append(app)
 app=apps[0]
 def run(op,tail=(),app=app,tool=T,ok=True,extra=None):return call([tool,op,'--manifest',app/'rnx.toml',*tail],dict(env,**(extra or {})),ok=ok)
 def document(name,app=app):return json.loads((app/name).read_text())
 def binary(app=app):
  r=document('.rnx/receipt.json',app)
  if r['format'] in [3,4]:
   i=json.loads(document('rnx.lock',app)['assembly']['identity']);return Path(i['context']['cache_root'])/'entries'/r['assembly_key']/'artifacts'/r.get('executable_blake3',r.get('executable_sha256'))
  return app/'.rnx/artifacts'/r.get('executable_blake3',r.get('executable_sha256'))
 run('lock',['--offline'],tool=OLD);run('build',['--offline'],tool=OLD)
 assert document('rnx.lock')['format']==2 and document('.rnx/receipt.json')['format']==3
 local=binary();baseline=[sha(app/'rnx.lock'),sha(app/'rnx.Cargo.lock'),sha(app/'.rnx/receipt.json'),sha(local)];localstat=local.stat()
 for path,name in [(app/'rnx.lock','genuine-old.lock.json'),(app/'.rnx/receipt.json','genuine-old.receipt.json')]:shutil.copyfile(path,O/name)
 oldreceipt=(app/'.rnx/receipt.json').read_bytes()
 def recovery(p):
  import shlex
  commands=[line for line in p.stderr.splitlines() if ' --manifest ' in line]
  assert [shlex.split(c) for c in commands]==[[str(T),'lock','--manifest',str(app/'rnx.toml')],[str(T),'build','--manifest',str(app/'rnx.toml')]],p.stderr
 for op,tail in [('run',[]),('session',['--no-splash','--color=never']),('eval',['--','hello']),('build',['--offline'])]:
  refusal=run(op,tail,ok=False);recovery(refusal);assert 'envelope format 2' in refusal.stderr
  assert not refusal.stdout
  assert baseline==[sha(app/'rnx.lock'),sha(app/'rnx.Cargo.lock'),sha(app/'.rnx/receipt.json'),sha(local)]
 results['genuine_lock2_receipt3_refuse_unchanged_exact_quoted_commands']=True
 run('lock',['--offline']);assert document('rnx.lock')['format']==3
 for op in ['run','eval','session']:
  p=run(op,['--','42'] if op=='eval' else [],ok=False);recovery(p);assert 'envelope format 3' in p.stderr
  assert (app/'.rnx/receipt.json').read_bytes()==oldreceipt
 prior_builds=len(buildlog.read_text().splitlines());run('build',['--offline']);assert len(buildlog.read_text().splitlines())==prior_builds+1;shared=binary();assert shared!=local and shared.stat().st_ino!=localstat.st_ino and local.exists() and sha(local)==baseline[-1]
 assert document('.rnx/receipt.json')['format']==4
 results['explicit_relock_fresh_key_no_promotion_old_artifact_retained']=True
 key=document('.rnx/receipt.json')['assembly_key'];entry=shared.parent.parent;ready=entry/'ready.json';readybytes=ready.read_bytes()
 for path,name in [(app/'rnx.lock','shared.lock.json'),(app/'.rnx/receipt.json','shared.receipt.json'),(ready,'shared.ready.json'),(app/'rnx.Cargo.lock','Cargo.lock')]:shutil.copyfile(path,O/name)
 # Tools absent at launch; only cargo -V and rustc -Vv allowed on attachment.
 traps=root/'traps';traps.mkdir();marker=root/'compiler-used'
 for name,arg in [('cargo','-V'),('rustc','-Vv')]:
  real=shutil.which(name);p=traps/name;p.write_text('#!/bin/sh\nif [ "$1" = "'+arg+'" ] && [ -z "$RNX_TRAP_ALL" ]; then exec '+real+' "$@"; fi\necho invoked >> '+str(marker)+'\nexit 91\n');p.chmod(0o755)
 trapped={'PATH':str(traps)+':'+env['PATH']}
 run('lock',['--offline'],app=apps[1]);run('run',app=apps[1],ok=False)
 p=run('build',['--offline'],app=apps[1],extra=trapped);assert 'attached shared' in p.stderr and binary(apps[1])==shared and not marker.exists()
 assert len(buildlog.read_text().splitlines())==prior_builds+1
 results['second_project_explicit_attachment_no_compilation']=True
 reads=root/'reads'
 def observed(op,tail=(),ok=True):
  reads.unlink(missing_ok=True)
  p=run(op,tail,ok=ok,extra=dict(trapped,RNX_TRAP_ALL='1',RNX_PROJECT_COUNT_ARTIFACT=str(shared),RNX_PROJECT_READ_LOG=str(reads)))
  return p,sum(map(int,reads.read_text().splitlines())) if reads.exists() else 0
 for op,tail in [('run',['--','arg']),('session',['--no-splash']),('eval',['--','two\n🦀'])]:
  assert observed(op,tail)[1]==0
  assert observed(op,['--verify',*tail])[1]==shared.stat().st_size
 assert not marker.exists();results['all_launch_modes_without_compiler']=True
 oldstat=shared.stat();os.utime(shared,ns=(oldstat.st_atime_ns,oldstat.st_mtime_ns+1000000));assert observed('eval',['--','42'])[1]==shared.stat().st_size;assert observed('eval',['--','42'])[1]==0
 original=shared.read_bytes();st=shared.stat();shared.write_bytes(original[:-1]+bytes([original[-1]^1]));os.utime(shared,ns=(st.st_atime_ns,st.st_mtime_ns));assert observed('eval',['--','42'])[1]==0;assert 'hash mismatch' in observed('eval',['--verify','--','42'],False)[0].stderr;shared.write_bytes(original);observed('eval',['--verify','--','42'])
 replacement=root/'replacement';shutil.copy2(shared,replacement);replacement.replace(shared);assert observed('eval',['--','42'])[1]==shared.stat().st_size
 results['stamp_verify_and_documented_inplace_miss']=True
 receipt=app/'.rnx/receipt.json';good=receipt.read_bytes()
 for changes in [{'format':2},{'assembly_key':'0'*64},{'executable_blake3':'0'*64},{'lock_blake3':'0'*64}]:
  bad=json.loads(good);bad.update(changes);receipt.write_text(json.dumps(bad));run('run',ok=False)
 receipt.write_bytes(good);results['receipt_bindings_refuse']=True
 # Refresh failure must retain old receipt, not a newly trusted stamp.
 st=shared.stat();os.utime(shared,ns=(st.st_atime_ns,st.st_mtime_ns+1000000));run('run',ok=False,extra={'RNX_PROJECT_FAIL':'before-receipt-refresh'});assert receipt.read_bytes()==good;run('run');results['refresh_failure_preserves_receipt']=True
 # Input checks precede artifact reads, including restored source timestamps.
 text=(app/'main.rn').read_bytes();st=(app/'main.rn').stat();(app/'main.rn').write_bytes(text.replace(b'42',b'43'));os.utime(app/'main.rn',ns=(st.st_atime_ns,st.st_mtime_ns));p,n=observed('eval',['--','42'],False);assert 'changed' in p.stderr and n==0;(app/'main.rn').write_bytes(text)
 results['full_source_checks']=True
 rust=native/'src/lib.rs';oldrust=rust.read_bytes();st=rust.stat();changed=oldrust.replace(b'for a in',b'for b in');assert changed!=oldrust and len(changed)==len(oldrust)
 rust.write_bytes(changed);os.utime(rust,ns=(st.st_atime_ns,st.st_mtime_ns))
 for tail in [['--','42'],['--verify','--','42']]:
  p,n=observed('eval',tail,False);assert 'changed' in p.stderr and n==0
 rust.write_bytes(oldrust);os.utime(rust,ns=(st.st_atime_ns,st.st_mtime_ns))
 results['restored_mtime_native_edit_refuses_before_artifact_in_both_modes']=True

 # Bad unused maps cannot block session/eval; run alone owns the map.
 maps=app/'.rnx/maps'
 for p in maps.glob('*.json'):p.write_text('broken')
 run('eval',['--','42']);run('session');run('run');results['interactive_map_scope']=True
 # Wrong root, new project Cargo config, retained ready corruption, deletion.
 run('run',ok=False,extra={'RNX_PROJECT_CACHE':str(root)})
 (app/'.cargo').mkdir();(app/'.cargo/config.toml').write_text('[net]\noffline=true\n');assert 'outside shared cache' in run('run',ok=False).stderr;(app/'.cargo/config.toml').unlink();(app/'.cargo').rmdir()
 ready.write_text('{}');run('run',ok=False);assert ready.read_text()=='{}';ready.write_bytes(readybytes)
 moved=root/'entry-held';entry.rename(moved);run('run',ok=False,extra=dict(trapped,RNX_TRAP_ALL='1'));assert not marker.exists();moved.rename(entry)
 results['cache_and_context_refusals_no_repair']=True
 # Attachment receipt failure preserves the shared entry and leaves no receipt.
 run('build',['--offline'],ok=False,extra={'RNX_PROJECT_FAIL':'before-shared-receipt'});assert not receipt.exists() and ready.read_bytes()==readybytes
 run('build',['--offline'],extra=trapped);results['receipt_publication_failure']=True
 def interrupted(op,tail,point,status):
  marker=root/'interrupt-pause';marker.unlink(missing_ok=True)
  p=subprocess.Popen([T,op,'--manifest',app/'rnx.toml',*tail],env=dict(env,RNX_PROJECT_PAUSE=point,RNX_PROJECT_PAUSE_FILE=str(marker)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  try:
   until=time.monotonic()+20
   while not marker.exists():
    assert p.poll() is None,(point,p.communicate());assert time.monotonic()<until;time.sleep(.01)
   p.send_signal(signal.SIGINT if status==130 else signal.SIGTERM);out,err=p.communicate(timeout=10);assert p.returncode==status and not out,(point,p.returncode,out,err)
  finally:
   if p.poll() is None:p.kill();p.communicate()
   marker.unlink(missing_ok=True)
 good=receipt.read_bytes();st=shared.stat();os.utime(shared,ns=(st.st_atime_ns,st.st_mtime_ns+1000000))
 interrupted('eval',['--verify','--','42'],'before-receipt-refresh',130);assert receipt.read_bytes()==good
 run('eval',['--','42'])
 interrupted('build',['--offline'],'before-shared-receipt',143);assert not receipt.exists() and ready.read_bytes()==readybytes
 run('build',['--offline'],extra=trapped)
 results['refresh_and_shared_attachment_interruption']=True

 # Pair publication rollback and signal mismatch detection use real new locks.
 oldpair=[(app/f).read_bytes() for f in ['rnx.lock','rnx.Cargo.lock']]
 cargo=native/'Cargo.toml';oldcargo=cargo.read_text();cargo.write_text(oldcargo.replace('0.0.0','0.0.1'))
 run('lock',['--offline'],ok=False,extra={'RNX_PROJECT_FAIL':'after-json-publication'});assert oldpair==[(app/f).read_bytes() for f in ['rnx.lock','rnx.Cargo.lock']]
 pause=root/'pause';p=subprocess.Popen([T,'lock','--offline','--manifest',app/'rnx.toml'],env=dict(env,RNX_PROJECT_PAUSE='after-cargo-publication',RNX_PROJECT_PAUSE_FILE=str(pause)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 until=time.monotonic()+30
 while not pause.exists():assert p.poll() is None and time.monotonic()<until;time.sleep(.01)
 p.send_signal(signal.SIGTERM);p.communicate(timeout=10);assert p.returncode==143;assert 'pair mismatch' in run('run',ok=False).stderr;pause.unlink();cargo.write_text(oldcargo);run('lock',['--offline']);run('build',['--offline'],extra=trapped)
 results['pair_atomicity_and_signal_recovery']=True
 # Overrides require an explicit verification build, with no Cargo invocation.
 copy=root/'override';shutil.copy2(local,copy);manifest=app/'rnx.toml';manifest.write_text('format=1\n[application]\nentry="main.rn"\n[executable]\npath="../override"\n')
 receipt.unlink();run('lock',['--offline'],tool=OLD);run('eval',['--','42'],tool=OLD)
 oldlock=(app/'rnx.lock').read_bytes();oldreceipt=receipt.read_bytes()
 for op in ['run','eval','session','build']:
  p=run(op,['--','42'] if op=='eval' else [],ok=False);recovery(p);assert (app/'rnx.lock').read_bytes()==oldlock and receipt.read_bytes()==oldreceipt
 run('lock',['--offline']);assert document('rnx.lock')['format']==3
 run('eval',['--','42'],ok=False);run('build',extra=dict(trapped,RNX_TRAP_ALL='1'));assert document('.rnx/receipt.json')['format']==4
 for op,tail in [('run',['--','42']),('eval',['--','42']),('session',[])]:run(op,tail,extra=dict(trapped,RNX_TRAP_ALL='1'))
 receipt.unlink();run('run',ok=False);run('build',extra=dict(trapped,RNX_TRAP_ALL='1'))
 good=receipt.read_bytes();saved=(app/'rnx.lock').read_bytes()
 for changes in [dict(format=99),dict(format=1),dict(extra=True)]:
  bad=json.loads(saved);bad.update(changes);(app/'rnx.lock').write_text(json.dumps(bad));badbytes=(app/'rnx.lock').read_bytes()
  run('build',ok=False);run('run',ok=False);assert receipt.read_bytes()==good and (app/'rnx.lock').read_bytes()==badbytes
 (app/'rnx.lock').write_bytes(saved)
 for changes in [dict(format=99),dict(executable_sha256='0'*64),dict(extra=True)]:
  bad=json.loads(good);bad.update(changes);receipt.write_text(json.dumps(bad));badbytes=receipt.read_bytes();run('run',ok=False);assert receipt.read_bytes()==badbytes
 receipt.write_bytes(good)
 st=copy.stat();content=copy.read_bytes();copy.write_bytes(content[:-1]+bytes([content[-1]^1]));os.utime(copy,ns=(st.st_atime_ns,st.st_mtime_ns))
 run('eval',['--','42']);assert 'hash mismatch' in run('eval',['--verify','--','42'],ok=False).stderr
 assert receipt.read_bytes()==good;copy.write_bytes(content);run('eval',['--verify','--','42'])
 results['genuine_override_migration_explicit_build_no_compiler_unknown_mixed_refusals']=True
 for status in [130,143]:
  interrupted('build',[],'after-build',status);assert not receipt.exists()
  run('build',extra=dict(trapped,RNX_TRAP_ALL='1'))
 run('build',ok=False,extra={'RNX_PROJECT_FAIL':'after-build'});assert not receipt.exists()
 run('build',extra=dict(trapped,RNX_TRAP_ALL='1'))
 assert not marker.exists()
 p=call(['cargo','build'],dict(env,**trapped),ok=False);assert marker.exists() and p.returncode==91;marker.unlink()
 results['override_build_failure_interrupt_and_compilation_trap_positive_control']=True

 shutil.copyfile(buildlog,O/'native-builds.log')
 shutil.copytree(native,O/'runtime',dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git'))
 (O/'contracts-conditions.json').write_text(json.dumps({'legacy_revision':'7cd3205','legacy_tool_sha256':sha(OLD),'new_tool_sha256':sha(T),'source_patch':'tool.patch','scope':'real commands with small argv-reporting runtime; no Polars timing claim'},indent=2)+'\n')
 (O/'contracts.json').write_text(json.dumps(results,indent=2)+'\n')
print('PASS',len(results),'command groups')
