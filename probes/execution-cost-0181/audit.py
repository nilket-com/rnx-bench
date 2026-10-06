"""Read-only 0181 closure audit. No counter opens, subject runs or host mutations.
Run from repository root: python3 probes/execution-cost-0181/audit.py
"""
import hashlib
import json
import pathlib
import statistics
import events0181 as driver

ROOT = pathlib.Path(__file__).resolve().parents[2]
RESULTS = ROOT / 'results/execution-cost-0181'
RAW_SHA = '4b83a82b650d0aa8739d0e6ac38e822719694d0e9ad3c46167b655ea17d0d418'


def require(ok, reason):
	if not ok:
		raise ValueError(reason)


def values(c, group, ops):
	# Independent same-sample formulas, including every quantity in the shared summary.
	v = dict(c)
	v['cycles_per_instruction'] = c['cycles'] / c['instructions']
	if ops:
		v.update(instructions_per_operation=c['instructions'] / ops, cycles_per_operation=c['cycles'] / ops)
	if group == 'C':
		v.update(branch_miss_rate=c['br_misp_retired_all'] / c['br_inst_retired_all'] if c['br_inst_retired_all'] else None,
			branches_per_instruction=c['br_inst_retired_all'] / c['instructions'])
		if ops:
			v.update(branch_misses_per_operation=c['br_misp_retired_all'] / ops, branches_per_operation=c['br_inst_retired_all'] / ops)
	if group == 'D':
		total = c['idq_dsb_uops'] + c['idq_mite_uops']
		v.update(dsb_share_of_dsb_plus_mite=c['idq_dsb_uops'] / total if total else None,
			icache_stall_cycles_per_cycle=c['icache_data_stalls'] / c['cycles'])
	if group == 'E':
		v.update(l1_miss_loads_per_instruction=c['mem_load_retired_l1_miss'] / c['instructions'],
			store_forward_blocks_per_instruction=c['ld_blocks_store_forward'] / c['instructions'])
		if ops:
			v.update(l1_miss_loads_per_operation=c['mem_load_retired_l1_miss'] / ops, store_forward_blocks_per_operation=c['ld_blocks_store_forward'] / ops)
	return v


def quantity(rows, key):
	by = {s: [r['values'][key] for r in rows if r['subject'] == s] for s in ('base', 'cand')}
	if any(v is None for vs in by.values() for v in vs):
		return {'status': 'undefined (zero denominator in at least one sample)'}
	b, c = (statistics.median(by[s]) for s in ('base', 'cand'))
	paired = [statistics.median(r['values'][key] for r in rows if r['subject'] == 'cand' and r['rep'] == rep) -
		statistics.median(r['values'][key] for r in rows if r['subject'] == 'base' and r['rep'] == rep) for rep in range(5)]
	q = statistics.quantiles(by['base'], n=10)
	width, delta = q[-1] - q[0], c - b
	return {'base_median': b, 'cand_median': c, 'difference': delta, 'relative': delta / b if b else None,
		'paired_contrasts': paired, 'base_p10_p90_width': width,
		'resolved': (all(x > 0 for x in paired) or all(x < 0 for x in paired)) and abs(delta) > width,
		'direction': 'up' if delta > 0 else 'down' if delta < 0 else 'none'}


def main():
	base = driver.base
	base.bind_subjects()  # Read-only hashes of retained binaries, input scripts and manifest.
	p = RESULTS / 'official1'
	raw = (p / 'raw.jsonl').read_bytes()
	require(hashlib.sha256(raw).hexdigest() == RAW_SHA, 'official raw hash')
	rows = [json.loads(l) for l in raw.splitlines()]
	report = json.loads((p / 'official.json').read_text())
	refs, outputs = base.references(), base.expected_stdout()
	expected = [(g, rep, label, side, tail, ops) for g in driver.ORDER for rep in range(5)
		for label, tail, _, ops in base.WORKLOADS for side in ('base', 'cand', 'cand', 'base')]
	require(len(rows) == len(expected) == 560, 'exact sample count')
	require(report['record'] == '0181' and report['status'] == 'COMPLETE', 'registered status')
	require(report['order'] == list(report['groups']) == driver.ORDER, 'group order')
	require(report['failed_groups'] == [] and report['complete_diagnostics'] == driver.DIAGNOSTICS, 'completed diagnostics')
	require(report['references'] == refs, '0179 references')
	require(report['env'] == base.E0 and 0 < report['ended'] - report['started'] < base.OFFICIAL_DEADLINE, 'phase/environment')
	admission = report['admission']
	require(admission['availability_sha256'] == driver.AVAILABILITY_SHA256 == base.sha(RESULTS / 'discovery1/availability.json'), 'availability pin')
	require(admission['identity_sha256'] == driver.IDENTITY_SHA256 == base.sha(RESULTS / 'discovery1/identity.json'), 'identity pin')
	require(admission['libraries'] == driver.library_gate(), 'library pins')
	manifest = driver.validate_availability(json.loads((RESULTS / 'discovery1/availability.json').read_text()), driver.IDENTITY_SHA256)
	require(manifest['order'] == report['order'], 'eligible order')
	identity = json.loads((RESULTS / 'discovery1/identity.json').read_text())
	require(admission['identity_fields_compared'] == sorted(identity), 'identity comparison fields')
	for receipt in [admission['perf_version_receipt']] + [report['groups'][g]['identity_recheck'] for g in driver.ORDER]:
		base.lifecycle(receipt)
		require(receipt['argv'] == ['perf', '--version'] and receipt['status'] == 0 and receipt['stdout'].strip() == identity['perf'], 'identity version receipt')
	by_group = {g: [] for g in driver.ORDER}
	for index, (r, e) in enumerate(zip(rows, expected)):
		g, rep, label, side, tail, ops = e
		require((r['group'], r['rep'], r['workload'], r['subject']) == e[:4] and r['kind'] == 'event', f'ordered sample {index}')
		require(r['hash'] == r['hash_after'] == base.PRIMARY[side][1], f'primary hashes {index}')
		require(r['argv'] == base.perf_argv(g) + [str(base.STAGE), *tail], f'argv {index}')
		require(r['env'] == base.E0 and r['controller_affinity'] == [4], f'E0/affinity {index}')
		base.lifecycle(r)
		require(r['status'] == 0 and r['stdout'] == outputs[label], f'status/output {index}')
		c = driver.classify(r['stderr'], g)
		by_group[g].append({**r, 'values': values(c, g, ops), 'counters': c, 'metrics': base.metrics(g, c, ops)})
	text = (RESULTS / 'OFFICIAL.md').read_text()
	checks, anchor_rows, printed_rows = 0, 0, 0
	selection = {}
	for g in driver.ORDER:
		require(report['groups'][g]['status'] == 'complete', 'group status ' + g)
		summary = base.summarize(g, by_group[g])
		require(summary == report['groups'][g]['summary'], 'shared summary reproduction ' + g)
		require(base.anchor_check(g, summary, refs) == report['groups'][g]['anchor_failures'] == [], 'shared anchors ' + g)
		selection[g] = {}
		for label, _, _, ops in base.WORKLOADS:
			x = [r for r in by_group[g] if r['workload'] == label]
			s = summary[label]
			require(set(s['quantities']) == set(x[0]['values']), 'quantity set')
			for key in x[0]['values']:
				q = quantity(x, key)
				require(q == s['quantities'][key], 'independent quantity ' + g + ' ' + label + ' ' + key)
				checks += 1
			for side in ('base', 'cand'):
				require(abs(s[side]['instructions'] / refs[label][side]['instructions'] - 1) <= .02 + 1e-12, 'independent instruction anchor')
				if label != 'run-empty':
					require(abs(s[side]['cycles'] / refs[label][side]['cycles'] - 1) <= .10 + 1e-12, 'independent cycle anchor')
			if label != 'run-empty':
				require(abs(s['instructions_change'] - refs[label]['instructions_change']) <= .005 + 1e-12, 'instruction effect anchor')
				require(abs(s['cycles_change'] - refs[label]['cycles_change']) <= .03 + 1e-12, 'cycle effect anchor')
			keys = {'R': [], 'C': ['br_inst_retired_all', 'br_misp_retired_all', 'branch_miss_rate'],
				'D': ['idq_dsb_uops', 'idq_mite_uops', 'dsb_share_of_dsb_plus_mite', 'icache_data_stalls', 'icache_stall_cycles_per_cycle'],
				'E': ['mem_load_retired_l1_miss', 'ld_blocks_store_forward', 'l1_miss_loads_per_instruction', 'store_forward_blocks_per_instruction']}[g]
			selection[g][label] = {k: s['quantities'][k] for k in keys}
			for key in keys:
				if g == 'E' and key.endswith('_per_instruction'):
					continue  # Ratios retained and independently checked above; OFFICIAL.md prints E raw counts only.
				q = quantity(x, key)
				verdict = ('resolved ' + q['direction']) if q['resolved'] else 'unresolved'
				rel = f"{q['relative']:+.2%}" if q['relative'] is not None else 'n/a'
				per = f"{q['difference'] / ops:+.3f}" if ops and key in x[0]['counters'] else ''
				contrasts = ', '.join(f'{v:+.4g}' for v in q['paired_contrasts'])
				line = f"| {label} | {key} | {q['base_median']:.6g} | {q['cand_median']:.6g} | {q['difference']:+.6g} | {rel} | {per} | {contrasts} | {q['base_p10_p90_width']:.4g} | {verdict} |"
				require(line in text, 'printed diagnostic table ' + g + ' ' + label + ' ' + key)
				printed_rows += 1
	for label, *_ in base.WORKLOADS:
		ss = [report['groups'][g]['summary'][label] for g in driver.ORDER]
		line = '| ' + ' | '.join([label, f"{refs[label]['cycles_change']:+.2%}", *[f"{s['cycles_change']:+.2%}" for s in ss],
			f"{refs[label]['instructions_change']:+.3%}", *[f"{s['instructions_change']:+.3%}" for s in ss]]) + ' |'
		require(line in text, 'printed anchor table ' + label)
		anchor_rows += 1
	scan = json.loads((p / 'sentinel-scan.json').read_text())
	require(scan == report['sentinel_scan'] and scan['completed'] and scan['occurrences'] == 0 and scan['files_with_occurrences'] == [], 'sentinel receipt')
	require((RESULTS / 'official1.status').read_text().strip() == 'exit 0', 'exit receipt')
	print(json.dumps({'completed': True, 'raw_sha256': RAW_SHA, 'rows': len(rows), 'group_rows': {g: len(rs) for g, rs in by_group.items()},
		'status': report['status'], 'independent_quantities_checked': checks, 'printed_anchor_rows': anchor_rows, 'printed_diagnostic_rows': printed_rows,
		'summaries_and_anchors': 'exactly reproduced; every quantity and anchor independently checked',
		'sentinel_scan_receipt': scan, 'subject_executions': 0, 'counter_opens': 0, 'diagnostics': selection}, indent=1))


if __name__ == '__main__':
	main()
