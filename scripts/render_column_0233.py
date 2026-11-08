"""Validate and render ADR 0233's instruction and disclosed timing evidence."""
import itertools
import json
from pathlib import Path
import re
import statistics as st

ROOT = Path(__file__).resolve().parents[1]
raw = (ROOT / 'results/column-0233-summary.json').read_text()
assert len(raw.encode()) < 1000000
assert not re.search(r'/(?:home|Users)/|[A-Z]:\\Users\\', raw)
s = json.loads(raw)
assert s['status'] == 'published'
for key in ('published', 'baseline', 'measured'):
	assert re.fullmatch('[0-9a-f]{40}', s[key])
assert s['runtime_equivalence']['final'] == s['published']
assert s['runtime_equivalence']['runtime_diff'] == []
assert len(s['receipts']) >= 14
assert all(re.fullmatch('[0-9a-f]{64}', x) for x in s['receipts'].values())
assert all(x == 'PASS' for x in s['final_gate_status'].values())
assert s['final_gate_status']['FINAL-v1/RESULT.json'] == 'PASS'
assert s['portable_delta_Ir_per_map'] == 6
layouts = ('flat', 'alternating', 'deterministic-random', 'sliced-chunked-null')
ops = ('eq', 'ne', 'lt', 'le', 'gt', 'ge')
expected = set(itertools.product((f'i64{o}_{f}' for o in ops for f in ('pair', 'right', 'left')), layouts, (65536, 10000000), (0, 1)))
xs = s['instruction_samples']
assert len(xs) == len(expected)
assert {(x['kind'], x['layout'], x['rows'], x['call']) for x in xs} == expected
assert all(0 < x['candidate_Ir_per_row'] < x['baseline_Ir_per_row'] for x in xs)
for collection, count in (('timing_samples', 80), ('investigation_samples', 40)):
	assert len(s[collection]) == count
	for x in s[collection]:
		assert len(x['times_ns']) == 6 and all(type(t) is int and t > 0 for t in x['times_ns'])
		assert re.fullmatch('[0-9a-f]{64}', x['sha256'])
		assert re.fullmatch('[0-9a-f]{64}', x['binary_sha256'])
timing_cells = {('i64eq', layout) for layout in layouts} | {('f64gt', 'flat'), ('f64gt', 'alternating'), ('mixedor', 'flat'), ('mixedor', 'alternating')}
assert {(x['kind'], x['layout'], x['role'], x['round']) for x in s['timing_samples']} == {(k, l, role, r) for k, l in timing_cells for role in ('baseline', 'candidate') for r in range(5)}
assert {(x['kind'], x['role'], x['round']) for x in s['investigation_samples']} == set(itertools.product(('f64gt', 'f64le'), ('baseline', 'candidate'), range(10)))
for x in s['investigation_samples']:
	assert len(x['counters']) == 6 and x['ticks_per_second'] == 100

def stats(collection, kind, layout, role, warm=True):
	times = [x['times_ns'] for x in s[collection] if (x['kind'], x['layout'], x['role']) == (kind, layout, role)]
	assert len(times) == (5 if collection == 'timing_samples' else 10)
	values = [st.median(t[1:]) if warm else t[0] for t in times]
	return st.median(values) / 1e6, min(values) / 1e6, max(values) / 1e6

def fmt(x):
	return f'{x[0]:.2f} [{x[1]:.2f}, {x[2]:.2f}]'

context = {x['engine']:x['warm_ms']['median'] for x in s['historical_context']}
assert set(context) == {'arrow','polars'}
assert s['historical_context_source'] == 'results/column-0224-summary.json'
lines = ['## Packed I64 comparisons — ADR 0233', '',
	f"Published rnx **`{s['published'][:8]}`** uses runtime-dispatched AVX2 for I64",
	'`==`, `!=`, `<`, `<=`, `>` and `>=`, including column/column and both constant',
	'orientations. Signed extremes, nulls, slices, chunks and tails retain bitwise',
	'parity; unsupported CPUs and forced-portable mode keep the scalar comparison.', '',
	'All six operations reduced total instruction counts in every tested layout',
	'at 64K and 10M rows, on first and warm calls. Live AVX2 symbols were checked.', '',
	'| Operation | Total instruction reduction across measured cases |', '|---|---:|']
for op in ops:
	gains = [100 * (1-x['candidate_Ir_per_row']/x['baseline_Ir_per_row']) for x in xs if x['kind'].startswith('i64'+op+'_')]
	lines.append(f'| {op} | {min(gains):.2f}–{max(gains):.2f}% |')
lines += ['', '**Timing caveat:** the original run accidentally kept the same binary order',
	'within each case. The scheduling formula canceled the intended alternation.',
	'These measurements are retained and disclosed, not described as counterbalanced.',
	'At 100M rows, five fresh processes per binary each made one first call and',
	'five warm calls, with a 120-second cooldown per round. Warm values below are',
	'the median [minimum, maximum] of the five process medians, in milliseconds.',
	'Input construction and full-output validation were outside the timed interval.', '',
	'| I64 equality layout | Baseline warm ms | Candidate warm ms | Change |', '|---|---:|---:|---:|']
for layout in layouts:
	a, b = (stats('timing_samples', 'i64eq', layout, role) for role in ('baseline', 'candidate'))
	lines.append(f'| {layout} | {fmt(a)} | {fmt(b)} | {100*(b[0]/a[0]-1):+.1f}% |')
lines += ['', '**Exact exceptions approved by the user:** shared F64 predicate dispatch',
	'adds 4/5 instructions per 1,024-row block for greater-than/less-or-equal,',
	'6/7 for arithmetic comparison, 9/10 for F64 AND, and 11/12 for mixed OR',
	'(flat/nonflat). Function-level setup constants and these slopes are pinned',
	'to the measured binary pair; +1 instruction, extra calls and extra slope fail.',
	'The original scalar/F64 comparison kernels remain unchanged: 246 protected',
	'routines passed resolved assembly identity. The shared driver is outside that set.', '',
	'A separate portable host probe measured all six operators at 4K/64K rows.',
	'Its total overhead is exactly **6 instructions per map**, with zero net slope:',
	'the driver gains `6 + 2×blocks`, offset by a helper changing from `30×blocks`',
	'to `28×blocks`. Its exact scorer also rejects redistribution hidden behind the',
	'same total. This probe uses its own paired binaries; it is not the CLI binary.', '',
	'**F64 timing investigation:** the original flat greater-than run reported a',
	'17% warm slowdown. A separate disclosed investigation alternated order across',
	'ten fresh processes per binary (five of each order), with the same cooldown.',
	'It did not reproduce that result. First-call medians remained higher for the',
	'candidate; overlapping ranges do not establish zero effect or statistical',
	'significance. The I64 timing above was not repeated.', '',
	'| F64 flat case | Call | Baseline ms | Candidate ms |', '|---|---|---:|---:|']
for kind in ('f64gt', 'f64le'):
	for warm in (False, True):
		a, b = (stats('investigation_samples', kind, 'flat', role, warm) for role in ('baseline', 'candidate'))
		lines.append(f"| {kind} | {'warm' if warm else 'first'} | {fmt(a)} | {fmt(b)} |")
lines += ['', 'The investigation also records per-call process CPU ticks and faults.',
	'CPU tick resolution is 10 ms; those counter intervals include snapshot overhead,',
	'while the wall timer excludes snapshots. No claim rests on sub-tick CPU changes.', '',
	'For **cross-day context only**, ADR 0224 measured flat 100M I64 equality at',
	f"about {context['polars']:.2f} ms for single-thread Polars and {context['arrow']:.2f} ms for direct Arrow, versus",
	f"the {stats('timing_samples', 'i64eq', 'flat', 'candidate')[0]:.2f} ms observed here for rnx. These are not matched same-day comparisons.",
	'Core, hardware parity, Miri, exact-vector/identity, host, integration, generated',
	'projects, cross and commit checks passed. Unchanged interpreter paths were not',
	're-measured. Unchanged-path system-library bands at 100M were not measured;',
	'the accepted coverage is SMALL vectors and the changed-path 64K/10M matrix.',
	'Failed exploratory captures and the original timing remain recorded.',
	'[Samples, exact pins, receipt hashes and caveats](results/column-0233-summary.json).',
	'[Renderer and validation](scripts/render_column_0233.py).']
block = '<!-- column-0233:start -->\n' + '\n'.join(lines) + '\n<!-- column-0233:end -->'
p = ROOT / 'README.md'; old = p.read_text()
if '<!-- column-0233:start -->' in old:
	new = re.sub(r'<!-- column-0233:start -->.*?<!-- column-0233:end -->', lambda _: block, old, flags=re.S)
else:
	assert '<!-- column-0230:start -->' in old
	new = old.replace('<!-- column-0230:start -->', block+'\n\n<!-- column-0230:start -->', 1)
p.write_text(new)
print('PASS: complete coverage, timing samples, exact exceptions, disclosures and privacy')
