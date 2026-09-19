"""Discriminate Cargo's checkout repair from product verification."""
from common import *
p=T/'tiny-a';lock=json.loads((p/'rnx.lock').read_text());root=Path(lock['git'][0]['checkout']);identity=json.loads(lock['assembly']['identity']);entry=Path(identity['context']['cache_root'])/'entries'/json.loads((p/'.rnx/receipt.json').read_text())['assembly_key']
f=root/'src/lib.rs';marker=root/'.cargo-ok';original=f.read_bytes();old_marker=marker.read_bytes() if marker.exists() else b''
# Restore this fixture's expected clean transport state, then change one byte.
assert b'fixture runtime' in original
edited=original.replace(b'fixture runtime',b'fixture runtimf');assert len(edited)==len(original) and edited!=original
rows=[]
try:
 for frontend in ['cargo','product']:
  for present in [True,False]:
   f.write_bytes(edited)
   if present:marker.write_bytes(old_marker)
   else:marker.unlink(missing_ok=True)
   before=f.read_bytes()
   args=['cargo','metadata','--locked','--offline','--format-version','1'] if frontend=='cargo' else [TOOL,'lock','--offline','--manifest',p/'rnx.toml']
   result=run(args,cwd=entry/'assembly' if frontend=='cargo' else None,ok=False)
   after=f.read_bytes();rows.append({'frontend':frontend,'marker_present_before':present,'status':result.returncode,'before_sha256':sha(before),'after_sha256':sha(after),'repaired':after==original,'stderr':result.stderr.decode()})
   if frontend=='cargo':assert result.returncode==0
   elif present:assert result.returncode and b'raw Git blob differs' in result.stderr
   else:assert result.returncode==0
   assert (after==original)==(not present),(frontend,present)
finally:
 f.write_bytes(original);marker.write_bytes(old_marker)
save('repair-stop.json',{'cargo':run(['cargo','-V']).stdout.decode().strip(),'source':str(root),'original_sha256':sha(original),'edited_sha256':sha(edited),'rows':rows,'conclusion':'Cargo metadata repairs an edited checkout when the transport marker is absent; post-resolution verification cannot detect the discarded bytes. Product candidate remains unaccepted.'})
print('Cargo repair boundary reproduced in all four controls',flush=True)
