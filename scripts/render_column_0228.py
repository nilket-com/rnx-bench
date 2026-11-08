"""Validate complete raw timing samples and render the explicit reuse report."""
import itertools
import json
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / 'results/column-0228-summary.json').read_text()
assert len(text.encode()) < 1000000
assert not re.search(r'/(?:home|Users)/|[A-Z]:\\Users\\', text)
s = json.loads(text)
kinds = ('f64const', 'f64add', 'f64chain')
layouts = ('flat', 'alternating')
roles = ('baseline', 'candidate', 'reuse')
assert len(s['samples']) == 90
assert {(x['kind'], x['layout'], x['role'], x['sample']) for x in s['samples']} == set(itertools.product(kinds, layouts, roles, range(5)))
assert len(s['table']) == 12
assert {(x['kind'], x['layout'], x['mode']) for x in s['table']} == set(itertools.product(kinds, layouts, ('first', 'warm')))
for x in s['samples']:
	assert len(x['times_ns']) == 6 and all(type(v) is int and v > 0 for v in x['times_ns'])
	assert re.fullmatch('[0-9a-f]{64}', x['sha256'])
for r in s['table']:
	for role in roles:
		times = [x['times_ns'] for x in s['samples'] if (x['kind'], x['layout'], x['role']) == (r['kind'], r['layout'], role)]
		values = [t[0] if r['mode'] == 'first' else statistics.median(t[1:]) for t in times]
		assert statistics.median(values) / 1e6 == r[role + '_ms']
		assert [min(values), max(values)] == r['range_ns'][role]
	assert abs(r['reuse_vs_candidate'] - r['reuse_ms'] / r['candidate_ms']) < 1e-14
for v in s['receipts'].values(): assert re.fullmatch('[0-9a-f]{64}', v)
for k in ('published', 'baseline'): assert re.fullmatch('[0-9a-f]{40}', s[k])
context = {}
source = json.loads((ROOT / 'results/column-0224-summary.json').read_text())
for engine in ('arrow','polars'):
	context[engine] = {}
	for kind in ('f64const','f64add','f64chain'):
		rows = [x for x in source['rows'] if x['engine'] == engine and x['kind'] == kind
			and x['layout'] == 'flat' and x['rows'] == 100000000
			and x['threads'] == 'single' and x['panel'] == 'equivalent']
		assert len(rows) == 1
		context[engine][kind] = rows[0]['warm_ms']['median']
reuse_rows = [x for x in s['table'] if (x['kind'],x['layout'],x['mode']) == ('f64chain','flat','warm')]
assert len(reuse_rows) == 1
reuse_chain = reuse_rows[0]['reuse_ms']
lines = ['## Explicit output reuse — ADR 0228', '',
'Published rnx **`' + s['published'][:8] + '`** adds consuming',
'`kernel.map_reusing(inputs, previous)` for eligible F64 outputs.',
'At 100M rows, warm calls save **38%** for flat const/add, **8%** for a flat',
'chain, and **21%** for a chain on nullable columns versus the same binary\'s',
'plain map. Nullable const/add still allocate fresh, as planned.', '',
'The caller supplies the previous output; there is no hidden buffer cache.',
'Reuse requires exclusive whole-buffer ownership and capacity between the',
'needed size and twice that size. Shared, sliced, non-F64 and unsuitable-size',
'donors fall back to fresh allocation. Rejected buffers are dropped before',
'fresh allocation; memory is not retained beyond caller-owned outputs.', '',
'Milliseconds: median [minimum, maximum] across five fresh processes.',
'Each process makes one first call and five warm calls; warm statistics use',
'each process\'s median. The first reuse call allocates fresh. Input creation,',
'preparation and full-output validation are outside timing. Role order',
'alternates by round with a fixed 120-second cooldown. No retries or',
'statistical-confidence claim. Baseline plain map is rnx `' + s['baseline'][:8] + '`.', '',
'| Expression | Layout | Call | Baseline plain ms | New plain ms | Reuse ms |',
'|---|---|---|---:|---:|---:|']
for r in s['table']:
	def fmt(role):
		lo, hi = r['range_ns'][role]
		return f"{r[role + '_ms']:.1f} [{lo / 1e6:.1f}, {hi / 1e6:.1f}]"
	lines.append(f"| {r['kind']} | {r['layout']} | {r['mode']} | {fmt('baseline')} | {fmt('candidate')} | {fmt('reuse')} |")
lines += ['',
'Warm page faults fall from **622–1,133 to 0–3** on the four eligible cells.',
'Nullable const/add remain at 1,133 in the separate diagnostic.', '',
'The user approved an exact instruction-count exception for plain map:',
'flat F64 const adds **1 instruction per 1,024-row block**; flat axpy and',
'I64 add add **2**. At 10M and 100M the total program deltas are exactly',
'`ceil(n/1024)+96`, `2*ceil(n/1024)+88`, and `2*ceil(n/1024)+98` respectively.',
'Fixed setup vectors for other paths are pinned too. Binary-pair checks',
'reject an extra instruction per call or block and changed call counts.',
'The affected instruction totals rise about **0.06–0.13%**. Plain-map warm',
'medians range from **0.96–1.02×** baseline; this does not prove zero timing cost.',
'Raw failures remain recorded alongside approved rescores.', '',
f"ADR 0224 warm medians: Arrow flat const {context['arrow']['f64const']:.1f} ms, add",
f"{context['arrow']['f64add']:.1f} ms and chain {context['arrow']['f64chain']:.1f} ms; single-thread Polars",
f"{context['polars']['f64const']:.1f}, {context['polars']['f64add']:.1f} and {context['polars']['f64chain']:.1f} ms respectively.",
f"Polars leads the flat-chain context result (about {context['polars']['f64chain']:.0f} ms",
f"versus {reuse_chain:.0f} ms for reuse).",
'These came from a **different run/day**, not this paired experiment.',
'The previously quoted 70/92/203/210 ms Arrow figures were from the instrumented',
'0228 diagnostic, not ADR 0224. This corrects that attribution; context does not',
'establish parity or a win over either engine.', '',
'Core, targeted Miri, ownership/retention, host, integration, generated-project,',
'cross and commit checks passed. Unchanged interpreter paths were not re-measured.',
'[Raw sample times, ranges, binary identities and receipt hashes](results/column-0228-summary.json).',
'[Renderer and validation](scripts/render_column_0228.py).']
block = '<!-- column-0228:start -->\n' + '\n'.join(lines) + '\n<!-- column-0228:end -->'
p = ROOT / 'README.md'; old = p.read_text()
if '<!-- column-0228:start -->' in old:
	new = re.sub(r'<!-- column-0228:start -->.*?<!-- column-0228:end -->', lambda _: block, old, flags=re.S)
else:
	assert '<!-- column-0227:start -->' in old
	new = old.replace('<!-- column-0227:start -->', block + '\n\n<!-- column-0227:start -->', 1)
p.write_text(new)
print('PASS: sample coverage, medians, ranges, identities, privacy and rendering')
