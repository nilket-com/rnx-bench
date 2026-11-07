"""Validate and render the ADR0221 publication table without private paths."""
import itertools
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / 'results/column-0221-summary.json').read_text()
assert not re.search(r'/(?:home|Users)/|[A-Z]:\\Users\\', text)
s = json.loads(text)
assert re.fullmatch('[0-9a-f]{64}', s['receipt_sha256'])
for key in ('published', 'baseline', 'measured_baseline', 'measured_candidate'):
	assert re.fullmatch('[0-9a-f]{40}', s[key])
keys = {(r['operation'], r['layout'], r['rows']) for r in s['rows']}
assert len(keys) == len(s['rows']) == 8
assert keys == set(itertools.product(('f64chain',), ('flat', 'sliced-chunked-null', 'alternating', 'deterministic-random'), (10000000, 100000000)))
lines = ['## Pure-F64 multi-operation plans — ADR 0221', '',
'Published rnx **`' + s['published'][:8] + '`** runs qualifying pure-F64 plans',
'with at least two Add/Sub/Mul operations in a separate whole-plan driver.',
'The measured expression is `x*2.0+y`; single-operation plans keep existing paths.', '',
'Whole-map executed instructions per row, including setup and system-library work.',
'Input construction, initial compilation and output validation are outside the',
'measured interval. First and warm are two map calls in each capture.',
'Baseline is published **`' + s['baseline'][:8] + '`**. No adjustments are subtracted.', '',
'| Operation | Layout | Rows | Baseline first | 0221 first | Baseline warm | 0221 warm |',
'|---|---|---:|---:|---:|---:|---:|']
for r in s['rows']:
	for role in ('baseline_Ir', 'candidate_Ir'):
		assert len(r[role]) == 2 and all(type(n) is int and n > 0 for n in r[role])
	values = [r['baseline_Ir'][0], r['candidate_Ir'][0], r['baseline_Ir'][1], r['candidate_Ir'][1]]
	lines.append('| ' + ' | '.join([r['operation'], r['layout'], str(r['rows'])] + [f'{n/r["rows"]:.6f}' for n in values]) + ' |')
lines += ['', 'Protected column paths passed exact function-vector checks with reviewed setup',
'constants and pinned run_flat-to-map inlining redistribution (net nonpositive',
'per block). Unknown-object totals stayed exact; system-library bands passed.',
'NaN bit equality was verified on x86-64 only, not asserted across platforms.', '',
'Output zero-initialization remains. Its measured 8 versus 0.44 Ir/row size',
'dependence is backlogged for attribution and a separate ownership change.', '',
'**Column-only scope: old interpreter paths were not re-measured. These are',
'instruction counts only, with no elapsed-time or cycle measurements. The gains',
'apply to qualifying pure-F64 plans, not arbitrary scripts.**', '',
'[Exact totals, measured/published commits and source receipt hash](results/column-0221-summary.json).', '']
section = '\n'.join(lines)
p = ROOT / 'README.md'; original = p.read_text()
start = '<!-- column-0221:start -->'; end = '<!-- column-0221:end -->'
block = start + '\n' + section + end + '\n\n'
if start in original:
	a = original.index(start); b = original.index(end, a) + len(end)
	updated = original[:a] + block.rstrip('\n') + original[b:]
else:
	a = original.index('<!-- column-0220:start -->'); updated = original[:a] + block + original[a:]
p.write_text(updated)
print('PASS: coverage, instruction totals, provenance and rendered table')
