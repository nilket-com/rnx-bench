"""Validate and render the write-only masked F64 paired measurements."""
import itertools
import json
from pathlib import Path
from archive_inputs import evidence
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]
text = (evidence('results/column-0229-summary.json')).read_text()
assert len(text.encode()) < 1000000
assert not re.search(r'/(?:home|Users)/|[A-Z]:\\Users\\',text)
s = json.loads(text)
assert s['status'] == 'published'
kinds = ('f64const','f64add')
layouts = ('alternating','deterministic-random','sliced-chunked-null')
roles = ('baseline','candidate')
assert len(s['samples']) == 60
assert {(x['kind'],x['layout'],x['role'],x['sample']) for x in s['samples']} == set(itertools.product(kinds,layouts,roles,range(5)))
assert len(s['table']) == 12
assert {(x['kind'],x['layout'],x['mode']) for x in s['table']} == set(itertools.product(kinds,layouts,('first','warm')))
for x in s['samples']:
	assert len(x['times_ns']) == 6 and all(type(n) is int and n > 0 for n in x['times_ns'])
	assert re.fullmatch('[0-9a-f]{64}',x['sha256'])
for x in s['table']:
	for role in roles:
		times = [a['times_ns'] for a in s['samples'] if (a['kind'],a['layout'],a['role']) == (x['kind'],x['layout'],role)]
		values = [t[0] if x['mode']=='first' else statistics.median(t[1:]) for t in times]
		assert statistics.median(values)/1e6 == x[role+'_ms']
		assert [min(values),max(values)] == x['range_ns'][role]
	assert abs(x['ratio'] - x['candidate_ms']/x['baseline_ms']) < 1e-14
assert len(s['faults']) == 36 and s['fault_policy_pass'] is False
for sha in s['receipts'].values(): assert re.fullmatch('[0-9a-f]{64}',sha)
for name in ('candidate','baseline'): assert re.fullmatch('[0-9a-f]{40}',s[name])
lines = ['## Write-only masked F64 output — ADR 0229','',
'Published rnx **`'+s['candidate'][:8]+'`** removes the output zero-prefill pass',
'from masked single-operation F64 const/add/sub/mul. Each block writes its',
'complete result, including positive-zero null lanes, before publication.',
'Reuse admission is unchanged; nullable const/add still allocate fresh.', '',
'At 100M rows, the measured const/add cases improve **16–25% on first calls**',
'and **17–29% on warm calls** versus `'+s['baseline'][:8]+'`.',
'Milliseconds below are median [minimum, maximum] across five fresh processes.',
'Each process makes one first and five warm calls; warm statistics use its',
'median. Construction and full-output validation are outside timing. Roles',
'alternate by round, with a fixed 120-second cooldown. There were no retries.',
'All twelve observed ranges are disjoint; this is not a confidence interval',
'or a guarantee for other machines. Raw condition flags are retained.', '',
'| Expression | Layout | Call | Baseline ms | Candidate ms | Reduction |',
'|---|---|---|---:|---:|---:|']
for x in s['table']:
	def fmt(role):
		lo,hi = x['range_ns'][role]
		return f"{x[role+'_ms']:.1f} [{lo/1e6:.1f}, {hi/1e6:.1f}]"
	lines.append(f"| {x['kind']} | {x['layout']} | {x['mode']} | {fmt('baseline')} | {fmt('candidate')} | {100*(1-x['ratio']):.1f}% |")
lines += ['',
'**Two explicit user-approved exceptions:** the sliced-chunked-null route',
'is judged by measured wall time instead of total instructions. At 10M rows',
'its 4,883 small memset calls write 40,000,000 null bytes; Callgrind counts',
'40 million REP-store iterations. The baseline uses one 80MB memset with',
'a different libc implementation path. The higher instruction count remains',
'reported; it was not erased or called a passing original gate. Other changed',
'layouts retain the total-instruction criterion. Exact binary-pair, program,',
'accounting and profile seals prevent widening this exception.', '',
'The strict no-more-page-faults rule also failed. Cold differences were',
'−4 to +3; one warm const sliced-null call rose from 1,319 to 1,383 (+64).',
'Every other warm count matched. These observations were accepted explicitly;',
'**no fault reduction or exact fault equality is claimed**. Exact fault pins',
'and +1 negative controls preserve the approved scope.', '',
'Core, targeted Miri, instance/identity, host, integration, generated-project,',
'cross and commit checks passed. Unchanged interpreter paths were not re-measured.',
'[Samples, ranges, faults, identities and receipt hashes](ARCHIVED-DATA.md?path=results/column-0229-summary.json#lookup).',
'[Renderer and validation](scripts/render_column_0229.py).']
block = '<!-- column-0229:start -->\n'+'\n'.join(lines)+'\n<!-- column-0229:end -->'
p = ROOT/'README.md';old = p.read_text()
if '<!-- column-0229:start -->' in old:
	new = re.sub(r'<!-- column-0229:start -->.*?<!-- column-0229:end -->',lambda _:block,old,flags=re.S)
else:
	assert '<!-- column-0228:start -->' in old
	new = old.replace('<!-- column-0228:start -->',block+'\n\n<!-- column-0228:start -->',1)
p.write_text(new)
print('PASS: coverage, samples, ranges, fault disclosure, privacy and rendering')
