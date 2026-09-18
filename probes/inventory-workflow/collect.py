"""Validate complete journals, pin the measured source, and summarize gates."""
from pathlib import Path
import json,hashlib,collections,subprocess as sp
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/inventory-workflow-0065'
rows=[json.loads(x) for x in (O/'samples.jsonl').read_text().splitlines()];m=json.loads((O/'measurement.json').read_text());assert len(rows)==3000==m['samples']
cells=collections.defaultdict(set)
for r in rows:
 k=(r['version'],r['count'],r['mode'],r['route'],r['repeat']);assert r['sample'] not in cells[k];cells[k].add(r['sample']);assert r['wall_ns']>0
assert len(cells)==100 and all(v==set(range(30)) for v in cells.values())
attach=[json.loads(x) for x in (O/'attachment-samples.jsonl').read_text().splitlines()];assert len(attach)==120
for v in ['baseline','current']:
 for rep in [0,1]:assert {r['sample'] for r in attach if r['version']==v and r['repeat']==rep}==set(range(30))
assert json.loads((O/'checks.json').read_text())['complete']
assert len(json.loads((O/'contracts.json').read_text()))==16
assert len(json.loads((O/'publication/results.json').read_text()))==37
real=json.loads((O/'real.json').read_text());assert real['shared_journey'] and real['override_journey']
setup=json.loads((O/'setup.json').read_text());assert len(setup)==4
for row in setup:
 paths={v:Path(row[v]['manifest']).parent/'rnx.Cargo.lock' for v in ['baseline','current']};assert paths['baseline'].read_bytes()==paths['current'].read_bytes()
 for v in ['baseline','current']:assert Path(row[v]['artifact']).is_file()
 root=next(t for t in row['trees'] if t['root'].endswith('/target/s'));assert root['files']==443 and root['bytes']==6988177
for version,b in m['binaries'].items():assert hashlib.sha256(Path(b['path']).read_bytes()).hexdigest()==b['sha256']
source=json.loads((O/'source.json').read_text())
for p,digest in source['files'].items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==digest
assert source['release_tool_sha256']==m['binaries']['current']['sha256']
summary=json.loads((O/'summary.json').read_text());observations=[]
for mode in ['run','eval','session']:
 for rep in [0,1]:
  groups={v:[r for r in summary if r['mode']==mode and r['repeat']==rep and r['version']==v] for v in ['baseline','current']}
  gains=[a['over_direct']-b['over_direct'] for a,b in zip(groups['baseline'],groups['current'])];assert all(g>0 for g in gains)
  observations.append(dict(mode=mode,repeat=rep,improvement_ms=gains,current_slope=groups['current'][0]['slope']))
(O/'completion.json').write_text(json.dumps(dict(complete=True,matched_cargo_locks=True,source_identity_checked=True,launch_samples=3000,preliminary_samples_retained=3000,attachment_samples=120,command_groups=16,publication_cases=37,observations=observations,qualification='format-only; nested reuse and its less-than-one-ms slope gate remain open'),indent=2)+'\n')
print('PASS complete matched gate 2 evidence')
