"""Validate and render the ADR0223 predicate report."""
import itertools
import json
from pathlib import Path
from archive_inputs import evidence
import re

ROOT = Path(__file__).resolve().parents[1]
text = (evidence('results/column-0223-summary.json')).read_text()
assert not re.search(r'/(?:home|Users)/|[A-Z]:\\Users\\', text)
s = json.loads(text)
for key in ('published', 'baseline', 'measured_baseline', 'measured_candidate'):
	assert re.fullmatch('[0-9a-f]{40}', s[key])
expressions = {'f64gt': 'x > 1.0', 'f64le': 'x <= 1.0', 'i64eq': 'x == 2', 'f64and': '(x > 1.0) & (y < 2.0)', 'mixedor': '((x > 1.0) & (y < 2.0)) | z', 'arithcmp': 'x * 2.0 + y > 3.0'}
layouts = ('flat', 'sliced-chunked-null', 'alternating', 'deterministic-random')
keys = {(r['operation'], r['layout'], r['rows']) for r in s['rows']}
assert len(keys) == len(s['rows']) == 48
assert keys == set(itertools.product(expressions, layouts, (10000000, 100000000)))
for name, receipt in s['receipts'].items():
	assert re.fullmatch('[0-9a-f]{64}', receipt['sha256'])
	assert receipt['status'] == ('FAIL' if name in ('diagnostic-v1/RESULT.json', 'large-v1/RESULT.json') else 'PASS')
lines = ['## Numeric predicate masks — ADR 0223', '',
'Published rnx **`' + s['published'][:8] + '`** adds a separate driver for Bool-output',
'plans containing I64/F64 comparisons, optionally F64 Add/Sub/Mul and Boolean',
'combinations. I64 arithmetic is excluded. The result is a Boolean mask column,',
'**not a row-filter operator**. Validity is the intersection of all input validity;',
'invalid output payload bits are zero.', '',
'| Fixture | Expression |', '|---|---|']
for name, expr in expressions.items():
	lines.append('| ' + name + ' | `' + expr.replace('|', '&#124;') + '` |')
lines += ['', 'Whole-map executed instructions per row, including setup and system-library work.',
'Construction, initial compilation and output validation are outside the interval.',
'First/warm are two map calls in each capture. Baseline is published **`' + s['baseline'][:8] + '`**.',
'No adjustments are subtracted. The table shows 100M rows; exact totals for both',
'10M and 100M are in the linked summary. Deterministic-random validity repeats a',
'256-bit mask; it is not an independent random draw per row.', '',
'| Predicate | Layout | Baseline first | 0223 first | Baseline warm | 0223 warm |',
'|---|---|---:|---:|---:|---:|']
for r in s['rows']:
	for role in ('baseline_Ir', 'candidate_Ir'):
		assert len(r[role]) == 2 and all(type(n) is int and n > 0 for n in r[role])
	if r['rows'] == 100000000:
		values = [r['baseline_Ir'][0], r['candidate_Ir'][0], r['baseline_Ir'][1], r['candidate_Ir'][1]]
		lines.append('| ' + ' | '.join([r['operation'], r['layout']] + [f'{n/r["rows"]:.6f}' for n in values]) + ' |')
lines += ['', 'All six predicates meet their absolute instruction ceilings and use at most',
'25% of baseline instructions across both sizes, all layouts and both calls.',
'Comparison forms were selected by measurement: F64 uses packed comparisons',
'over 64-lane words; I64 retains bounded eight-lane scalar comparisons because',
'the tested packed SSE2 form cost more. F64 arithmetic uses packed four-lane loops.', '',
'The original small and large FAIL receipts are retained with hashes. The small',
'rescore applies reviewed, binary-pair-pinned per-function setup constants and',
'exact call counts, with no per-row allowance. Untouched `dismantle_repr` source',
'showed a fixed instruction decrease attributed to code-generation redistribution.',
'The large rescore classifies the unchanged `f64chain` path under the ELF-object',
'rule: program instructions decreased by seven, unknown-object totals matched,',
'and system-library variation stayed within the existing band (0.001 Ir/row plus',
'4,096 fixed instructions). Its absolute whole-map ceiling remains enforced.',
'Neither rescore reran measurements or changed raw totals.', '',
'Core tests, targeted Miri, executed assembly snapshots, protected column checks,',
'host integration, generated projects and cross verification passed.',
'NaN behavior and bit equality were checked on x86-64; this is not a portable',
'NaN-payload guarantee. These are instruction counts only: no new timing result',
'or proportional elapsed-time claim is made.', '',
'**Column-only scope: old interpreter paths were not re-measured. These gains do',
'not describe arbitrary scripts or the cost of materializing filtered rows.**', '',
'[Exact totals, measured/published commits and retained receipt hashes](ARCHIVED-DATA.md?path=results/column-0223-summary.json#lookup).', '']
p = ROOT / 'README.md'
original = p.read_text()
start, end = '<!-- column-0223:start -->', '<!-- column-0223:end -->'
block = start + '\n' + '\n'.join(lines) + end
if start in original:
	a = original.index(start); b = original.index(end, a) + len(end)
	updated = original[:a] + block + original[b:]
else:
	a = original.index('<!-- column-0222:start -->')
	updated = original[:a] + block + '\n\n' + original[a:]
p.write_text(updated)
print('PASS: coverage, positive totals, receipt provenance and rendering')
