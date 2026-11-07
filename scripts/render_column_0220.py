"""Validate and render the ADR0220 publication table without private paths."""
import itertools
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / 'results/column-0220-summary.json').read_text()
assert not re.search(r'/(?:home|Users)/|[A-Z]:\\Users\\', text)
s = json.loads(text)
assert re.fullmatch('[0-9a-f]{64}', s['receipt_sha256'])
for key in ('published', 'baseline', 'measured_baseline', 'measured_candidate'):
	assert re.fullmatch('[0-9a-f]{40}', s[key])
keys = {(r['operation'], r['layout'], r['rows']) for r in s['rows']}
assert len(keys) == len(s['rows']) == 24
assert keys == set(itertools.product(('booland', 'boolor', 'boolchain'), ('flat', 'sliced-chunked-null', 'alternating', 'deterministic-random'), (10000000, 100000000)))
lines = ['## Packed Boolean plans — ADR 0220', '',
'Published rnx **`' + s['published'][:8] + '`** evaluates pure-Boolean AND/OR plans',
'and their NOT intermediates as packed words in a separate whole-plan driver.',
'Null semantics remain strict: all inputs must be valid for an output row to be valid.',
'NOT-only plans, comparisons, XOR and numeric plans keep their existing paths.', '',
'Whole-map executed instructions per row, including setup and system-library work.',
'Input construction, initial kernel compilation and output validation are outside',
'the measured interval. First and warm are the two map calls in each capture.',
'Baseline is published **`' + s['baseline'][:8] + '`**. No adjustments are subtracted.', '',
'| Operation | Layout | Rows | Baseline first | 0220 first | Baseline warm | 0220 warm |',
'|---|---|---:|---:|---:|---:|---:|']
for r in s['rows']:
	for role in ('baseline_Ir', 'candidate_Ir'):
		assert len(r[role]) == 2 and all(type(n) is int and n > 0 for n in r[role])
	values = [r['baseline_Ir'][0], r['candidate_Ir'][0], r['baseline_Ir'][1], r['candidate_Ir'][1]]
	lines.append('| ' + ' | '.join([r['operation'], r['layout'], str(r['rows'])] + [f'{n/r["rows"]:.6f}' for n in values]) + ' |')
lines += ['', 'Protected column paths passed exact function-vector checks with reviewed fixed',
'setup differences and the pinned beneficial invoke formula; unknown-object totals',
'matched and unchanged-path system-library bands passed. This is not a claim of',
'byte-identical binaries or identical setup cost.', '',
'**Column-only scope: old interpreter paths were not re-measured. These are instruction',
'counts only; no wall-clock or cycle measurements were taken for this record. Gains',
'apply to qualifying pure-Boolean plans, not arbitrary scripts.**', '',
'[Exact totals, measured/published commits and source receipt hash](results/column-0220-summary.json).', '']
section = '\n'.join(lines)
p = ROOT / 'README.md'; original = p.read_text()
start = '<!-- column-0220:start -->'; end = '<!-- column-0220:end -->'
block = start + '\n' + section + end + '\n\n'
if start in original:
	a = original.index(start); b = original.index(end, a) + len(end)
	updated = original[:a] + block.rstrip('\n') + original[b:]
else:
	a = original.index('<!-- column-0215:start -->'); updated = original[:a] + block + original[a:]
p.write_text(updated)
print('PASS: coverage, instruction totals, provenance and rendered table')
