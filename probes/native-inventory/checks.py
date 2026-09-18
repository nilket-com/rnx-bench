"""Copied tools preserve tests, locks and all uninstrumented source bytes."""
from pathlib import Path
import subprocess as sp,json,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/native-inventory-0065';rows=[]
for name in ['stock','timed']:
 p=W/name/'tools/project'
 for label,args in [('fmt',['cargo','fmt','--manifest-path',str(p/'Cargo.toml'),'--','--check']),('clippy',['cargo','clippy','--locked','--offline','--manifest-path',str(p/'Cargo.toml'),'--all-targets','--features','test-support','--','-D','warnings']),('tests',['cargo','test','--locked','--offline','--manifest-path',str(p/'Cargo.toml'),'--features','test-support','--','--test-threads=1'])]:
  with (O/(name+'-'+label+'.log')).open('w') as f:r=sp.run(args,stdout=f,stderr=sp.STDOUT,timeout=600)
  rows.append(dict(copy=name,check=label,status=r.returncode));(O/'checks.json').write_text(json.dumps(rows,indent=2)+'\n');print(name,label,r.returncode,flush=True);assert r.returncode==0
 allowed={'main.rs','lib.rs','assembly_probe.rs','fingerprint.rs','inventory.rs','workflow.rs'} if name=='timed' else set()
 for f in (R/'tools/project/src').rglob('*.rs'):
  rel=f.relative_to(R/'tools/project/src')
  if str(rel) not in allowed:assert f.read_bytes()==(p/'src'/rel).read_bytes(),(name,rel)
 assert (p/'Cargo.lock').read_bytes()==(R/'tools/project/Cargo.lock').read_bytes()
print('PASS copied source correspondence and configurations')
