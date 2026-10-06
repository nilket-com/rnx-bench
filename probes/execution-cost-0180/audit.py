"""Read-only closure audit: retained rows and tables only, never executes a subject or opens a counter.
Run from the repository root: python3 probes/execution-cost-0180/audit.py
"""
import hashlib
import json
import pathlib
import statistics
import events

ROOT = pathlib.Path(__file__).resolve().parents[2] / 'results/execution-cost-0180'
RAW_SHA = 'edfa125ad3ae2aeedc464f313f071d2d8c28d76a9884395402857c99723e83e0'


def require(ok, reason):
	if not ok:
		raise ValueError(reason)


def main():
	p = ROOT / 'official1'
	raw = (p / 'raw.jsonl').read_bytes()
	require(hashlib.sha256(raw).hexdigest() == RAW_SHA, 'official raw hash')
	rows = [json.loads(line) for line in raw.splitlines()]
	report = json.loads((p / 'official.json').read_text())
	require(len(rows) == 405, 'retained row count')
	expected = [(g, rep, label, side, tail, ops) for g in events.GROUPS for rep in range(5)
		for label, tail, _, ops in events.WORKLOADS for side in ('base', 'cand', 'cand', 'base')]
	outputs, refs = events.expected_stdout(), events.references()
	require(report['references'] == refs, '0179 references')
	samples = {g: [] for g in events.GROUPS}
	failed = []
	for i, (r, e) in enumerate(zip(rows, expected)):
		g, rep, label, side, tail, ops = e
		require((r['group'], r['rep'], r['workload'], r['subject']) == e[:4], 'ordered prefix')
		require(r['hash'] == r['hash_after'] == events.PRIMARY[side][1], 'subject hash')
		require(r['argv'] == events.perf_argv(g) + [str(events.STAGE), *tail], 'sample argv')
		require(r['env'] == events.E0 and r['controller_affinity'] == [4], 'environment/affinity')
		require(r['status'] == 0 and r['stdout'] == outputs[label], 'status/output')
		events.lifecycle(r)
		c = events.parse(r['stderr'], g)
		try:
			m = events.metrics(g, c, ops)
		except events.Stop as error:
			require(i == 404 and g == 'B', 'unexpected validity failure')
			failed.append({'row': i + 1, 'group_sample': 125, 'sum': sum(c[n] for n in events.TOPDOWN) / c['slots'], 'failure': str(error)})
			continue
		samples[g].append({**r, 'counters': c, 'metrics': m})
	require(len(failed) == 1 and list(report['groups']) == ['R', 'A'], 'STOP boundary')
	for g in ('R', 'A'):
		s = events.summarize(g, samples[g])
		require(s == report['groups'][g]['summary'], 'retained summary ' + g)
		require(events.anchor_check(g, s, refs) == report['groups'][g]['anchor_failures'] == [], 'anchors ' + g)
	text = (ROOT / 'OFFICIAL.md').read_text()
	for label, *_ in events.WORKLOADS:
		r, a = (report['groups'][g]['summary'][label] for g in ('R', 'A'))
		line = f"| {label} | {refs[label]['cycles_change']:+.2%} | {r['cycles_change']:+.2%} | {a['cycles_change']:+.2%} | {refs[label]['instructions_change']:+.3%} | {r['instructions_change']:+.3%} | {a['instructions_change']:+.3%} |"
		require(line in text, 'printed anchor table ' + label)
		for name in ('cycles_per_ref_cycle', 'ref_cycles_per_instruction', 'task_clock', 'context_switches'):
			# Reconstruct the A table independently from per-row ratios/counts, not its stored summary.
			x = [s for s in samples['A'] if s['workload'] == label]
			def value(s):
				c = s['counters']
				if name == 'cycles_per_ref_cycle':
					return c['cycles'] / c['ref_cycles']
				if name == 'ref_cycles_per_instruction':
					return c['ref_cycles'] / c['instructions']
				return c[name]
			vals = {side: [value(s) for s in x if s['subject'] == side] for side in ('base', 'cand')}
			b, c = (statistics.median(vals[side]) for side in ('base', 'cand'))
			paired = [statistics.median(value(s) for s in x if s['subject'] == 'cand' and s['rep'] == rep) - statistics.median(value(s) for s in x if s['subject'] == 'base' and s['rep'] == rep) for rep in range(5)]
			q = statistics.quantiles(vals['base'], n=10)
			width = q[-1] - q[0]
			resolved = (all(v > 0 for v in paired) or all(v < 0 for v in paired)) and abs(c - b) > width
			verdict = ('resolved up' if c > b else 'resolved down') if resolved else 'unresolved'
			relative = f'{(c - b) / b:+.2%}' if b else 'n/a'
			contrasts = ', '.join(f'{v:+.4g}' for v in paired)
			line = f'| {label} | {name} | {b:.6g} | {c:.6g} | {relative} | {contrasts} | {width:.4g} | {verdict} |'
			require(line in text, 'printed A table ' + label + ' ' + name)
	scan = json.loads((p / 'sentinel-scan.json').read_text())
	require(report['sentinel_scan'] == scan and scan['completed'] and scan['occurrences'] == 0, 'scan receipt')
	require(report['status'] == 'STOPPED (infrastructure, safety or measurement failure)', 'STOP status')
	require((ROOT / 'official1.status').read_text().strip() == 'exit 1', 'exit receipt')
	print(json.dumps({'completed': True, 'raw_sha256': RAW_SHA, 'rows': len(rows), 'groups': {g: sum(r['group'] == g for r in rows) for g in events.GROUPS}, 'stop': failed[0], 'R_A_summaries_and_anchors': 'exactly reproduced', 'printed_tables': '7 anchor rows and 28 A rows independently checked', 'sentinel_scan': scan, 'subject_executions': 0}, indent=1))


if __name__ == '__main__':
	main()
