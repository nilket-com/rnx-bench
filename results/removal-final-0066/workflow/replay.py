"""Replay the accepted command matrix with explicit 0065 migration expectations.
The generated driver is archived so every changed assertion is reviewable.
"""
from pathlib import Path
import subprocess as sp,json,hashlib
H=Path('/home/me/work/rnx-bench/probes/removal-final/target/workflow');B=Path('/home/me/work/rnx-bench');O=B/'results/removal-final-0066/workflow';P=B/'probes/cache-commands/check.py';s=P.read_text()
s=s.replace("H=Path(__file__).resolve().parent;B=H.parents[1]",f"H=Path({str(H)!r});B=Path({str(B)!r})")
s=s.replace("OLD=H/'target/legacy-tool'", "OLD=B/'probes/native-inventory/target/stock/tools/project/target/release/rnx-project'")
s=s.replace("O=B/'results/cache-commands-0061'", "O=B/'results/removal-final-0066/workflow'")
s=s.replace("root/name", "root/(name+\" space'quote\")")
s=s.replace("if r['format']==3:","if r['format'] in [3,4]:")
s=s.replace("r['executable_sha256']", "r.get('executable_blake3',r.get('executable_sha256'))")
a=s.index(" assert document('rnx.lock')['format']==1");b=s.index(" key=document('.rnx/receipt.json')",a)
s=s[:a]+''' assert document('rnx.lock')['format']==2 and document('.rnx/receipt.json')['format']==3
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
''' + s[b:]
s=s.replace("'executable_sha256':'0'*64", "'executable_blake3':'0'*64").replace("'lock_sha256':'0'*64", "'lock_blake3':'0'*64")
a=s.index(' # Overrides stay');b=s.index(' shutil.copyfile(buildlog',a)
s=s[:a]+''' # Overrides require an explicit verification build, with no Cargo invocation.
 copy=root/'override';shutil.copy2(local,copy);manifest=app/'rnx.toml';manifest.write_text('format=1\\n[application]\\nentry="main.rn"\\n[executable]\\npath="../override"\\n')
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
''' +s[b:]
s=s.replace("'legacy_revision':'814d20f'", "'legacy_revision':'7cd3205'")
s=s.replace("'source_patch':'source.patch'", "'source_patch':'tool.patch'")
s=s.replace("(O/'conditions.json')", "(O/'contracts-conditions.json')").replace("(O/'results.json')","(O/'contracts.json')")
# Add interruption cases to the current format receipt paths.
needle="results['receipt_publication_failure']=True"
s=s.replace(needle,needle+"""
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
""")
needle=" results['genuine_override_migration_explicit_build_no_compiler_unknown_mixed_refusals']=True"
s=s.replace(needle,needle+"""
 for status in [130,143]:
  interrupted('build',[],'after-build',status);assert not receipt.exists()
  run('build',extra=dict(trapped,RNX_TRAP_ALL='1'))
 run('build',ok=False,extra={'RNX_PROJECT_FAIL':'after-build'});assert not receipt.exists()
 run('build',extra=dict(trapped,RNX_TRAP_ALL='1'))
 assert not marker.exists()
 p=call(['cargo','build'],dict(env,**trapped),ok=False);assert marker.exists() and p.returncode==91;marker.unlink()
 results['override_build_failure_interrupt_and_compilation_trap_positive_control']=True
""")
needle="results['full_source_checks']=True"
s=s.replace(needle,needle+"""
 rust=native/'src/lib.rs';oldrust=rust.read_bytes();st=rust.stat();changed=oldrust.replace(b'for a in',b'for b in');assert changed!=oldrust and len(changed)==len(oldrust)
 rust.write_bytes(changed);os.utime(rust,ns=(st.st_atime_ns,st.st_mtime_ns))
 for tail in [['--','42'],['--verify','--','42']]:
  p,n=observed('eval',tail,False);assert 'changed' in p.stderr and n==0
 rust.write_bytes(oldrust);os.utime(rust,ns=(st.st_atime_ns,st.st_mtime_ns))
 results['restored_mtime_native_edit_refuses_before_artifact_in_both_modes']=True
""")
p=O/'contracts-driver.py';p.write_text(s)
with (O/'contracts.log').open('w') as f:sp.run(['python3',str(p)],check=True,stdout=f,stderr=sp.STDOUT)
(O/'contracts-adaptation.json').write_text(json.dumps(dict(source=str(P.relative_to(B)),sha256=hashlib.sha256(P.read_bytes()).hexdigest(),generated=p.name,changes=['baseline tool 7cd3205 generates real lock2/receipt3 and override lock1/receipt2','old launches and build must refuse with files unchanged, shell-parsed recovery commands','new formats 3/4 and renamed fields','explicit override build rather than implicit launch receipt creation','unknown and mixed documents refuse without publication']),indent=2)+'\n')
print('PASS current-format command and migration matrix')
