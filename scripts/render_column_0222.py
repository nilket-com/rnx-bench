"""Validate and render the ADR0222 publication table without private paths."""
import itertools
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / 'results/column-0222-summary.json').read_text()
assert not re.search(r'/(?:home|Users)/|[A-Z]:\\Users\\', text)
s = json.loads(text)
assert re.fullmatch('[0-9a-f]{64}', s['receipt_sha256'])
for key in ('published', 'baseline', 'measured_baseline', 'measured_candidate'):
	assert re.fullmatch('[0-9a-f]{40}', s[key])
keys = {(r['operation'], r['layout'], r['rows']) for r in s['rows']}
assert len(keys) == len(s['rows']) == 8
assert keys == set(itertools.product(('f64chain',), ('flat', 'sliced-chunked-null', 'alternating', 'deterministic-random'), (10000000, 100000000)))
lines = ['## F64 write-only output — ADR 0222', '',
'Published rnx **`' + s['published'][:8] + '`** runs qualifying pure-F64 plans',
'with at least two Add/Sub/Mul operations using write-only output storage.',
'The measured expression is `x*2.0+y`; single-operation plans keep existing paths.', '',
'Whole-map executed instructions per row, including setup and system-library work.',
'Input construction, initial compilation and output validation are outside the',
'measured interval. First and warm are two map calls in each capture.',
'Baseline is published **`' + s['baseline'][:8] + '`**. No adjustments are subtracted.', '',
'| Operation | Layout | Rows | Baseline first | 0222 first | Baseline warm | 0222 warm |',
'|---|---|---:|---:|---:|---:|---:|']
for r in s['rows']:
	for role in ('baseline_Ir', 'candidate_Ir'):
		assert len(r[role]) == 2 and all(type(n) is int and n > 0 for n in r[role])
	values = [r['baseline_Ir'][0], r['candidate_Ir'][0], r['baseline_Ir'][1], r['candidate_Ir'][1]]
	lines.append('| ' + ' | '.join([r['operation'], r['layout'], str(r['rows'])] + [f'{n/r["rows"]:.6f}' for n in values]) + ' |')
assert re.fullmatch('[0-9a-f]{64}', s['timing_receipt_sha256'])
assert set(s['retained_timing_failures']) == {'v1','v2','v3'}
assert all(re.fullmatch('[0-9a-f]{64}', v) for v in s['retained_timing_failures'].values())
keys = {(t['layout'],t['role']) for t in s['timings']}
assert len(keys) == len(s['timings']) == 8
assert keys == set(itertools.product(('flat','sliced-chunked-null','alternating','deterministic-random'),('baseline','candidate')))
lines += ['', 'Descriptive quiet 100M-row map wall time in milliseconds. One sample per',
'role/layout, containing first and warm calls; no statistical claim or timing',
'acceptance threshold. The lease and readiness policy used a fixed 120-second',
'cooldown before each sample. Construction and validation are outside map time.', '',
'| Layout | Version | First ms | Warm ms |', '|---|---|---:|---:|']
for t in s['timings']:
	assert len(t['map_ms'])==2 and all(type(v) is int and v>=0 for v in t['map_ms'])
	assert re.fullmatch('[0-9a-f]{64}',t['binary_sha256'])
	lines.append('| '+t['layout']+' | '+('0221' if t['role']=='baseline' else '0222')+' | '+' | '.join(map(str,t['map_ms']))+' |')
lines += ['', 'Timing recovery: v1 lacked clocks in mixed-null fixtures; v2 used an invalid',
'small fixture size; v3 put preflight artifacts in the recorder directory.',
'All three FAIL receipts were retained. Four completed, validated flat/sliced',
'samples were reused with receipt and binary identity checks; only missing',
'mixed-layout samples were measured after correcting the harness.', '',
'The removed fill measured 8 Ir/row at small sizes (Callgrind counts repeated',
'byte stores) and 0.4375 Ir/row at large sizes (glibc non-temporal stores).',
'Both paths write 8 bytes per row: removing the fill avoids a redundant 800 MB',
'pass at 100M rows. Ir savings do not express memory traffic or predict timing.', '',
'Protected column vectors passed with reviewed fixed setup pins, exact unknown',
'object totals and unchanged system-library bands. Every candidate F64 profile',
'lacked the output-fill edge; baseline profiles supplied the positive control.',
'NaN bit equality was verified on x86-64 only. Boolean output is unchanged.', '',
'**Column-only scope: old interpreter paths were not re-measured. Gains apply',
'only to qualifying pure-F64 plans, not arbitrary scripts.**', '',
'[Exact totals, timing samples, commits and receipt hashes](results/column-0222-summary.json).', '']
section = '\n'.join(lines)
p = ROOT / 'README.md'; original = p.read_text()
start = '<!-- column-0222:start -->'; end = '<!-- column-0222:end -->'
block = start + '\n' + section + end + '\n\n'
if start in original:
	a = original.index(start); b = original.index(end, a) + len(end)
	updated = original[:a] + block.rstrip('\n') + original[b:]
else:
	a = original.index('<!-- column-0221:start -->'); updated = original[:a] + block + original[a:]
p.write_text(updated)
print('PASS: coverage, instruction totals, provenance and rendered table')
