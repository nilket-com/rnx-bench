"""Render ADR 0226 from its reviewed 100M table; check raw totals and privacy."""
import itertools
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / 'results/column-0226-summary.json').read_text()
assert not re.search(r'/(?:home|Users)/|[A-Z]:\\Users\\', text)
s = json.loads(text)
kinds = ('booland', 'boolor', 'boolchain', 'booleq', 'boolne', 'boolxor')
layouts = ('flat', 'sliced-chunked-null', 'alternating', 'deterministic-random')
raw = {(r['kind'], r['layout'], r['rows'], r['role']): r['Ir'] for r in s['raw_totals']}
assert len(raw) == len(s['raw_totals']) == 96
assert set(raw) == set(itertools.product(kinds, layouts, (10000000, 100000000), ('baseline', 'candidate')))
assert len(s['table']) == 24
assert {(r['kind'], r['layout']) for r in s['table']} == set(itertools.product(kinds, layouts))
for r in s['table']:
	for role, call in itertools.product(('baseline', 'candidate'), range(2)):
		assert r[role + ('_first' if call == 0 else '_warm')] == raw[r['kind'], r['layout'], 100000000, role][call] / 100000000
for value in s['receipts'].values(): assert re.fullmatch('[0-9a-f]{64}', value)
for key in ('published', 'baseline'): assert re.fullmatch('[0-9a-f]{40}', s[key])
lines = ['## Packed Boolean XOR and equality — ADR 0226', '',
'Published rnx **`' + s['published'][:8] + '`** adds `^`, `==` and `!=` to the',
'pure-Boolean packed driver, including chains with `&`, `|` and `!`.',
'Equality uses word-wise XNOR; XOR and inequality use XOR. Strict input-null',
'intersection, zero invalid payload and tail masking are preserved. Numeric',
'comparison plans remain in the separate predicate driver.', '',
'Whole-map executed instructions per row, including system-library work.',
'First/warm are two map calls per capture. Construction, initial compilation',
'and output validation are outside the measured interval. Baseline is',
'**`' + s['baseline'][:8] + '`**, runtime-identical to measured `45823dda`.',
'No adjustments are subtracted. This is **Ir only, column-only scope**:',
'no new wall-time or unchanged interpreter performance claim.', '',
'| Shape | Layout | Baseline first | Candidate first | Baseline warm | Candidate warm |',
'|---|---|---:|---:|---:|---:|']
for r in s['table']:
	lines.append('| ' + r['kind'] + ' | ' + r['layout'] + ' | ' + ' | '.join(f"{r[k]:.6f}" for k in ('baseline_first','candidate_first','baseline_warm','candidate_warm')) + ' |')
lines += ['', 'The table shows 100M rows. All new shapes pass at 10M and 100M, first and',
'warm, across all four layouts: at most 2 Ir/row flat, 4 nullable, and 10% of',
'baseline instructions. Deterministic-random validity repeats a 256-bit mask.', '',
'The edited driver increases existing AND/OR/chain work by **6/3/13 instructions',
'per 1,024-row block** in the small diagnostic. Those paths retain their raw',
'ceilings: 2/4 Ir per row for AND/OR and 2.5/5 for chains, flat/nullable.',
'Unchanged paths retain exact function vectors plus reviewed fixed setup pins.', '',
'This record also repairs two stale cross-check fixtures left by ADR 0224,',
'whose gate set omitted cross: the live `src/time.rs` fingerprint and the',
'registry count after adding `time::monotonic_ns`. The checked refresh verifies',
'exact old/new witnesses, allowing only that addition and the source-proven',
'`monotonic_ms` documentation change. Historical provenance is unchanged.',
'Failed receipts are retained; cross passed after repair. Other passed stages',
'were reused with tooling-only diff proofs.', '',
'[Exact totals, reviewed table, binary identities and receipt hashes](results/column-0226-summary.json).',
'[Renderer and validation](scripts/render_column_0226.py).']
block = '<!-- column-0226:start -->\n' + '\n'.join(lines) + '\n<!-- column-0226:end -->'
p = ROOT / 'README.md'; old = p.read_text()
if '<!-- column-0226:start -->' in old:
	new = re.sub(r'<!-- column-0226:start -->.*?<!-- column-0226:end -->', lambda _: block, old, flags=re.S)
else:
	new = old.replace('<!-- column-0224:start -->', block + '\n\n<!-- column-0224:start -->', 1)
p.write_text(new)
print('PASS: coverage, exact totals, reviewed table, privacy, rendering')
