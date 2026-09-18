"""Repeat real full-hash attachment and shared/override Polars sessions."""
from pathlib import Path
import json,subprocess as sp,sys
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target/attachment';O=B/'results/inventory-final-0065/attachment';assert not W.exists();W.mkdir();O.mkdir()
rows=json.loads((B/'results/inventory-workflow-0065/setup.json').read_text());(O/'setup.json').write_text(json.dumps(rows));(O/'tools.json').write_text(json.dumps({'baseline':{'path':str(B/'probes/native-inventory/target/stock/tools/project/target/release/rnx-project')},'current':{'path':str(H/'target/tool')}}));(W/'env.json').write_bytes((H/'target/env.json').read_bytes())
p=B/'probes/inventory-workflow/real.py';s=p.read_text().replace("H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/inventory-workflow-0065'",f"H=Path({str(H)!r});B=Path({str(B)!r});W=Path({str(W)!r});O=Path({str(O)!r})",1);dest=O/'real-driver.py';dest.write_text(s)
with (O/'run.log').open('w') as f:sp.run([sys.executable,dest],stdout=f,stderr=sp.STDOUT,check=True)
print('PASS final attachment with compilation traps and shared/override Polars sessions',flush=True)
