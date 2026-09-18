"""Gate-4 exact matrix against product private test-support entry."""
from pathlib import Path
import subprocess as sp,shlex,json
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/nested-product-0065';W.mkdir(exist_ok=True);O.mkdir(exist_ok=True)
T=W/'nested-probe';T.write_text('#!/bin/sh\nexec '+shlex.quote(str(R/'tools/project/target/debug/rnx-project-assembly-probe'))+' nested-inventory "$@"\n');T.chmod(0o700)
for name in ['check','extra']:
 s=(B/'probes/nested-inventory'/f'{name}.py').read_text()
 s=s.replace("H=Path(__file__).resolve().parent;B=H.parents[1];",f"H=Path({str(H)!r});B=Path({str(B)!r});")
 s=s.replace("O=B/'results/nested-inventory-0065'",f"O=Path({str(O)!r})").replace("T=H/'target/tool/tools/project/target/release/nested-probe'",f"T=Path({str(T)!r})")
 p=O/f'{name}-driver.py';p.write_text(s)
 with (O/(name+'.log')).open('w') as log:sp.run(['python3',p],stdout=log,stderr=sp.STDOUT,check=True)
 print('PASS product',name,flush=True)
(O/'replay.json').write_text(json.dumps(dict(primary=len(json.loads((O/'matrix.json').read_text())),topology=len(json.loads((O/'extra.json').read_text())),entry=str(T),adaptation='isolated paths and private product probe instead of copied candidate; assertions unchanged'),indent=2)+'\n')
