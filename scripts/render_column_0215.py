"""Validate and render ADR0215 public evidence without machine-specific paths."""
import itertools
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / 'results/column-0215-summary.json'
text = p.read_text()
assert not re.search(r'/(?:home|Users)/|[A-Z]:\\Users\\', text)
s = json.loads(text)
assert s['published'] == '956ed4d5e89611ccb7140c54d4861390c94db49b'
assert s['measured'] == '89182b3b3235cdbf66b3312f844792608d6f1e12'
kinds = ('i64add', 'axpy', 'f64const', 'f64add', 'multiply3', 'boolnot')
layouts = ('flat', 'alternating', 'deterministic-random', 'sliced-chunked-null')
roles = ('original', 'baseline', 'candidate')
index = {(x['kind'], x['rows'], x['layout'], x['role']): x for x in s['matrix']}
assert len(index) == len(s['matrix']) == 144
assert set(index) == set(itertools.product(kinds, (10000000, 100000000), layouts, roles))
for x in s['matrix']:
	assert len(x['calls']) == 2
	for c in x['calls']:
		assert c['Ir'] == c['program_Ir'] + c['system_Ir'] + c['unknown_Ir'] > 0
		assert re.fullmatch('[0-9a-f]{64}', c['profile_sha256'])
timings = {(x['kind'], x['role']): x['map_ms'] for x in s['timing']}
assert len(timings) == len(s['timing']) == 12
assert set(timings) == set(itertools.product(kinds[:4], roles))
assert len(s['limitations']) == 6 and len(s['receipts']) == 13
assert all(x['status'] == 'PASS' and re.fullmatch('[0-9a-f]{64}', x['sha256']) for x in s['receipts'])
labels = dict(i64add='I64 x+1', axpy='I64 x*2+y', f64const='F64 x+1.0', f64add='F64 x+y')
lines = ['## Flat numeric output initialization — ADR 0215', '',
'Published rnx **`956ed4d5`** removes the initial zero fill for specialized flat',
'numeric outputs. Each primitive writes its whole block before the output becomes',
'visible. Generic, masked and Boolean outputs keep initialized storage. The record',
'also makes bounded null clearing explicit and separates masked-float entry signatures.', '',
'Whole-map instructions per row at **100 million rows**, including adaptation,',
'per-map preparation, allocation and worker join; input construction, initial',
'kernel compilation and output validation are outside the measured interval.', '',
'| Kernel | 0214 first / warm | 0216 first / warm | 0215 first / warm | Warm reduction vs 0216 |',
'|---|---:|---:|---:|---:|']
for k in kinds[:4]:
	values = [index[k,100000000,'flat',r]['calls'] for r in roles]
	cells = [' / '.join(f"{c['Ir']/100000000:.3f}" for c in v) for v in values]
	gain = 100 * (1 - values[2][1]['Ir'] / values[1][1]['Ir'])
	lines.append('| '+labels[k]+' | '+' | '.join(cells)+f' | {gain:.1f}% |')
lines += ['', 'Quiet single-process-sample wall times for the same 100M-row map, in milliseconds',
'(first / warm). These are descriptive observations, not statistical estimates.', '',
'| Kernel | 0214 | 0216 | 0215 |', '|---|---:|---:|---:|']
for k in kinds[:4]:
	lines.append('| '+labels[k]+' | '+' | '.join(' / '.join(map(str,timings[k,r])) for r in roles)+' |')
lines += ['', 'The complete 10M/100M matrix passed reviewed program checks against both baselines,',
'whole-map ceilings and applicable system-library checks. Unchanged paths retain',
'reviewed, exactly attributed setup costs of 17–82 instructions per call; no per-row',
'or per-block allowance was needed. Correctness, targeted Miri and host checks passed.', '',
'[Complete matrix, first/warm timings and evidence hashes](results/column-0215-summary.json).', '',
'Limitations from the approved publication packet:', '']
lines += ['- '+x for x in s['limitations']]
lines += ['', 'Measured candidate: `'+s['measured']+'`. The published commit adds only the reviewed',
'scorer, policy and tests. This is not a new cross-runtime comparison.', '']
report='\n'.join(lines)
readme=ROOT/'README.md';old=readme.read_text();start='<!-- column-0215:start -->';end='<!-- column-0215:end -->'
block=start+'\n'+report+'\n'+end+'\n\n'
if start in old:
	a=old.index(start);b=old.index(end,a)+len(end);old=old[:a]+block.rstrip()+old[b:]
else:
	pos=old.index('## Constant integer arithmetic');old=old[:pos]+block+old[pos:]
readme.write_text(old)
print('PASS:144 matrix cases,12 timing cases,13 receipt hashes; report rendered')
