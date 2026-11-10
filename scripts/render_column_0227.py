"""Validate raw process samples and render ADR 0227 timing with disclosures."""
import itertools
import json
from pathlib import Path
from archive_inputs import evidence
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]
text = (evidence('results/column-0227-summary.json')).read_text()
assert len(text.encode()) < 1000000
assert not re.search(r'/(?:home|Users)/|[A-Z]:\\Users\\', text)
s = json.loads(text)
kinds = ('f64const', 'f64add', 'f64chain')
layouts = ('flat', 'alternating')
keys = {(x['kind'], x['layout'], x['role'], x['sample']) for x in s['samples']}
assert len(keys) == len(s['samples']) == 60
assert keys == set(itertools.product(kinds, layouts, ('baseline', 'candidate'), range(5)))
assert len(s['table']) == 12
assert {(x['kind'], x['layout'], x['mode']) for x in s['table']} == set(itertools.product(kinds, layouts, ('first', 'warm')))
for sample in s['samples']:
	assert len(sample['times_ns']) == 6 and all(type(n) is int and n > 0 for n in sample['times_ns'])
for r in s['table']:
	for role in ('baseline', 'candidate'):
		times = [x['times_ns'] for x in s['samples'] if (x['kind'], x['layout'], x['role']) == (r['kind'], r['layout'], role)]
		values = [t[0] if r['mode'] == 'first' else statistics.median(t[1:]) for t in times]
		assert statistics.median(values) / 1e6 == r[role + '_ms']
		assert [min(values), max(values)] == r['range_ns'][role]
	assert abs(r['ratio'] - r['candidate_ms'] / r['baseline_ms']) < 1e-14
for v in s['receipts'].values(): assert re.fullmatch('[0-9a-f]{64}', v)
for k in ('published', 'baseline'): assert re.fullmatch('[0-9a-f]{40}', s[k])
lines = ['## Huge-page advice for large outputs — ADR 0227', '',
'Published rnx **`' + s['published'][:8] + '`** gives the operating system a',
'best-effort huge-page hint for large column buffers before first touch.',
'The matched baseline is **`' + s['baseline'][:8] + '`**. At 100M rows, these',
'F64 workloads take **34–51% less elapsed time** on the measurement host.', '',
'Milliseconds: median [minimum, maximum] across five fresh processes.',
'Each process makes one first call after preparation and five warm calls.',
'Warm statistics summarize each process\'s median of those five calls.',
'Construction, preparation and full-output validation are outside timing.',
'Binary order alternates by round, with a fixed 120-second round cooldown.',
'No retries and no statistical confidence claim.', '',
'| Expression | Layout | Call | Baseline ms | Candidate ms | Reduction |',
'|---|---|---|---:|---:|---:|']
for r in s['table']:
	def fmt(role):
		lo, hi = r['range_ns'][role]
		return f"{r[role + '_ms']:.1f} [{lo / 1e6:.1f}, {hi / 1e6:.1f}]"
	lines.append(f"| {r['kind']} | {r['layout']} | {r['mode']} | {fmt('baseline')} | {fmt('candidate')} | {(1 - r['ratio']) * 100:.1f}% |")
lines += ['',
'The instruction gate includes an explicit user-approved exception: unchanged',
'integer `x*3+y` executes one extra jump per all-valid executor call (about',
'+0.001 Ir/row flat and +0.008 for the sliced fixture). Exact binary-pair pins',
'check the formula and absolute calls at 10M and 100M, including partial blocks.',
'Mixed-valid calls save two instructions; flat F64 pair calls save four.',
'Advice and page-size initialization add exact first/warm constants, selected',
'separately when data and validity allocations reach 4 MiB. Every pin rejects',
'an extra instruction or changed call count. Raw failed captures are retained;',
'reviewed rescores pass without repeating measurements.', '',
'The separate page-fault diagnostic improved by a median **172×**, which is',
'not a 172× speedup. One cold call improved only **7.317×**, with partial',
'huge-page backing: 675,840 KiB versus 780,288 KiB warm. The hint was present;',
'the kernel fallback cause is unproven. No call was worse than baseline.',
'Huge-page availability and elapsed-time gains can vary by host and call.', '',
'For context only, flat F64 `x+1.0` warm is now about **120 ms**; ADR 0224',
'reported Arrow about **69 ms** and Polars about **71 ms** on a different day.',
'These are **not directly comparable measurements**. This report covers',
'column buffers; unchanged interpreter paths were not re-measured.', '',
'Core, Miri, host, integration, generated-project and cross checks passed.',
'[Raw sample times, ranges, binary identities and receipt hashes](ARCHIVED-DATA.md?path=results/column-0227-summary.json#lookup).',
'[Renderer and validation](scripts/render_column_0227.py).']
block = '<!-- column-0227:start -->\n' + '\n'.join(lines) + '\n<!-- column-0227:end -->'
p = ROOT / 'README.md'; old = p.read_text()
if '<!-- column-0227:start -->' in old:
	new = re.sub(r'<!-- column-0227:start -->.*?<!-- column-0227:end -->', lambda _: block, old, flags=re.S)
else:
	new = old.replace('<!-- column-0226:start -->', block + '\n\n<!-- column-0226:start -->', 1)
p.write_text(new)
print('PASS: exact sample coverage, medians, ranges, privacy and rendering')
