"""Validate and render the masked F64 reuse paired measurements."""
import itertools
import json
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / 'results/column-0230-summary.json').read_text()
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
assert len(s['faults']) == 18 and s['fault_policy_pass'] is False
for sha in s['receipts'].values(): assert re.fullmatch('[0-9a-f]{64}',sha)
for name in ('candidate','baseline','published'): assert re.fullmatch('[0-9a-f]{40}',s[name])
assert len(s['phases']) == 4
assert {(x['kind'],x['call']) for x in s['phases']} == set(itertools.product(kinds,(1,2)))
assert all(x['output_run'] == x['transfer'] == x['validity'] == 0 for x in s['phases'])
assert all(x['total'] == x['before_validity'] + x['outer_setup'] for x in s['phases'])
required = ('host-chain-v1/RESULT.json','final-integration-v1/RESULT.json','COMMIT-CHECK.json','PUBLICATION-PROOF.json')
for name in required:
	assert name in s['receipts'] and s['final_gate_status'][name] == 'PASS'
assert s['runtime_equivalence'] == dict(measured=s['candidate'], published=s['published'], changed_files=[])
gains = [100*(1-x['ratio']) for x in s['table'] if x['mode']=='warm']
assert len(gains) == 6 and min(gains) > 0
gain_min,gain_max = min(gains),max(gains)
lines = ['## Reuse for masked F64 outputs — ADR 0230', '',
'Published rnx **`'+s['published'][:8]+'`** admits masked single-operation F64',
'const/add/sub/mul outputs to `kernel.map_reusing(inputs, previous)`.',
'The existing rules remain: exclusive whole-buffer donors, nonzero output,',
'needed length ≤ capacity ≤ twice needed length, capacity charged once,',
'and fresh allocation on refusal. There is no hidden buffer cache or retention.', '',
f'At 100M rows, warm reuse is **{gain_min:.0f}–{gain_max:.0f}% faster** for all six measured nullable',
'const/add cells. Plain map and reuse use the **same candidate binary**.',
'Plain-map instruction vectors match the published baseline `'+s['baseline'][:8]+'`',
'exactly in the 4K/64K comparison; no instruction exception was needed.', '',
'Milliseconds: median [minimum, maximum] across five fresh processes.',
'Each process makes one first call and five warm calls; warm statistics use',
'its median. First reuse calls allocate fresh; their observed ranges overlap',
'plain map, and no first-call speedup is claimed. Construction and full-output',
'validation are outside timing. Role order alternates; cooldown is 120 seconds',
'per round. No retries or statistical-confidence claim. Condition flags remain',
'in the summary.', '',
'| Expression | Layout | Call | Plain map ms | Reuse ms |',
'|---|---|---|---:|---:|']
for x in s['table']:
	def fmt(role):
		lo,hi = x['range_ns'][role]
		return f"{x[role+'_ms']:.1f} [{lo/1e6:.1f}, {hi/1e6:.1f}]"
	lines.append(f"| {x['kind']} | {x['layout']} | {x['mode']} | {fmt('baseline')} | {fmt('candidate')} |")
lines += ['',
'**Fault-scope correction approved by the user:** the original ≤1% total warm',
'fault rule passed for alternating/random columns (1,133 plain faults versus',
'zero with reuse), but failed for sliced-null: reuse retained **465–762 total',
'faults**, versus 1,087–1,830 plain. That original FAIL remains recorded.',
'A separate phase capture found a stable donated pointer and capacity, with',
'**zero faults in warm output execution and transfer**. Its residual faults',
'occurred before validity intersection, in bitmap/setup allocation; a single',
'add call also had one outer-setup fault. The bitmap is 12.5 MB at 100M rows.',
'The phase probe does not identify every allocation within that span.',
'The revised sliced-null criterion covers output faults, while total faults',
'remain reported. It does not claim zero faults for the complete call.', '',
'| Kind | Warm call | Total faults (phase probe) | Before validity | Outer setup | Output execution | Transfer |',
'|---|---:|---:|---:|---:|---:|---:|']
for x in s['phases']:
	lines.append('| '+' | '.join(str(x[k]) for k in ('kind','call','total','before_validity','outer_setup','output_run','transfer'))+' |')
lines += ['',
'Bitwise/Path parity, donor fallback, refusal, cancellation, retention, core,',
'Miri, instance/identity, host, integration, generated-project, cross and',
'commit checks passed. Unchanged interpreter paths were not re-measured.',
'[Samples, ranges, total faults, phase attribution and receipt hashes](results/column-0230-summary.json).',
'[Renderer and validation](scripts/render_column_0230.py).']
assert f'**{gain_min:.0f}–{gain_max:.0f}% faster**' in '\n'.join(lines)
block = '<!-- column-0230:start -->\n'+'\n'.join(lines)+'\n<!-- column-0230:end -->'
p = ROOT/'README.md';old = p.read_text()
if '<!-- column-0230:start -->' in old:
	new = re.sub(r'<!-- column-0230:start -->.*?<!-- column-0230:end -->',lambda _:block,old,flags=re.S)
else:
	assert '<!-- column-0229:start -->' in old
	new = old.replace('<!-- column-0229:start -->',block+'\n\n<!-- column-0229:start -->',1)
p.write_text(new)
print('PASS: coverage, samples, ranges, phase/fault disclosure, privacy and rendering')
