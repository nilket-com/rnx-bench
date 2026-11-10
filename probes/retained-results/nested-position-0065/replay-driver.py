"""Gate-4 exact matrix against product private test-support entry."""
from pathlib import Path
import subprocess as sp,shlex,json
H=Path('/home/me/work/rnx-bench/probes/nested-position');B=Path('/home/me/work/rnx-bench');R=B.parent/'rnx';W=H/'target';O=B/'results/nested-position-0065';W.mkdir(exist_ok=True);O.mkdir(exist_ok=True)
T=W/'nested-probe';T.write_text('#!/bin/sh\nexec '+shlex.quote(str(R/'tools/project/target/debug/rnx-project-assembly-probe'))+' nested-inventory "$@"\n');T.chmod(0o700)
for name in ['check','extra']:
 s=(B/'probes/nested-inventory'/f'{name}.py').read_text()
 s=s.replace("H=Path(__file__).resolve().parent;B=H.parents[1];",f"H=Path({str(H)!r});B=Path({str(B)!r});")
 s=s.replace("O=B/'results/nested-inventory-0065'",f"O=Path({str(O)!r})").replace("T=H/'target/tool/tools/project/target/release/nested-probe'",f"T=Path({str(T)!r})")
 if name == 'extra':
  s=s.replace("pair('ignored-nested-repository',[p,p/'a']);assert sum('git' in x for x in r[1]['events'])==6","pair('ignored-nested-repository',[p,p/'a']);assert sum('git' in x for x in r[1]['events'])==3")
  s=s.replace('range(4097)', 'range(14000)').replace('discovery-limit-fallback', 'ignored-build-14000-eligible')
  s=s.replace("pair('ignored-build-14000-eligible',[p,p/'a']);assert sum('git' in x for x in r[1]['events'])==6","pair('ignored-build-14000-eligible',[p,p/'a']);assert sum('git' in x for x in r[1]['events'])==3")
 p=O/f'{name}-driver.py';p.write_text(s)
 with (O/(name+'.log')).open('w') as log:sp.run(['python3',p],stdout=log,stderr=sp.STDOUT,check=True)
 print('PASS product',name,flush=True)
(O/'replay.json').write_text(json.dumps(dict(primary=len(json.loads((O/'matrix.json').read_text())),topology=len(json.loads((O/'extra.json').read_text())),entry=str(T),adaptation='isolated paths and product private probe; ignored nested repository and 14000 ignored build files require eligibility under F3, with exact tree and allowance equality retained'),indent=2)+'\n')
