"""Independent read-only reconstruction of 0178's retained deciding samples, each same-profile pair."""
import collections
import hashlib
import json
import pathlib
import statistics
import sys


def read(path):
	return json.loads(path.read_text())


def counters(raw):
	values = {}
	for line in raw.splitlines():
		if not line.startswith('{'):
			continue
		row = json.loads(line)
		for name in ('instructions', 'cycles'):
			if row.get('event') in (name + ':u', 'cpu_core/' + name + '/u'):
				assert 99 <= float(row['pcnt-running']) <= 100
				assert name not in values
				values[name] = float(row['counter-value'])
	assert set(values) == {'instructions', 'cycles'}
	return values


def main(root):
	root = pathlib.Path(root)
	raw = [json.loads(line) for line in (root / 'raw.jsonl').read_text().splitlines()]
	result, pmu, wall = (read(root / name) for name in ('measure.json', 'pmu.json', 'wall.json'))
	profile, source = root.name.split('-')
	assert profile in ('p0', 'p1') and source in ('s75', 's76')
	roles = {'base': profile + '-base', 'cand': profile + '-' + source}
	assert result['pair'] == {'profile': profile, 'source': source, 'roles': roles}
	for row in raw:
		assert row['controller_affinity'] == [4]
		assert row['env'] == {'PATH': '/usr/bin:/bin', 'HOME': '/home/me', 'LANG': 'C.UTF-8'}
		if row['kind'] == 'reproduction-fifo':
			assert row['child_affinity'] == [4]
			assert row['child_status'] == 0 and row['counter_status'] == -2
			assert row['child_reaped'] and row['counter_reaped']
			assert not row['child_survivors'] and not row['counter_survivors']
			counters(row['counter_raw'])
		else:
			assert row['reaped'] and not row['group_survivors']
			assert not row['timed_out'] and not row['interrupted']
		if row.get('hash_after'):
			assert row['hash'] == row['hash_after']
			assert row['hash'] == result['manifest']['binaries'][roles[row['subject']] + '-primary']

	instructions = {}
	for workload, summary in pmu.items():
		rows = [row for row in raw if row['kind'] == 'pmu' and row['workload'] == workload]
		assert len(rows) == 20
		for rep in range(5):
			assert [r['subject'] for r in rows if r['rep'] == rep] == ['base', 'cand', 'cand', 'base']
		for name in ('instructions', 'cycles'):
			for subject in ('base', 'cand'):
				vals = [counters(r['stderr'])[name] for r in rows if r['subject'] == subject]
				assert len(vals) == 10 and vals == summary[name][subject]
				assert statistics.median(vals) == summary[name][subject + '_median']
			assert summary[name]['change'] == summary[name]['cand_median'] / summary[name]['base_median'] - 1
		instructions[workload] = summary['instructions']['change']

	for workload, summary in wall.items():
		rows = [row for row in raw if row['kind'] == 'wall' and row['workload'] == workload]
		assert len(rows) == 12
		values = {'base': [], 'cand': []}
		for rnd in range(3):
			order = ['base', 'cand', 'cand', 'base'] if rnd != 1 else ['cand', 'base', 'base', 'cand']
			assert [r['subject'] for r in rows if r['round'] == rnd] == order
		for row in rows:
			lines = row['stdout'].splitlines()
			assert len(lines) == 30 and row['status'] == 0
			plan = row['plan'].splitlines()
			assert plan[0] == '5'
			for i in range(5):
				receipt = lines[i * 6:(i + 1) * 6]
				assert receipt[0] == 'EXEC ' + str(i)
				assert receipt[1] == ' '.join(a.encode().hex() for a in row['target_argv'])
				assert int(receipt[3]) == 0
				assert bytes.fromhex(receipt[5]) == b''
				values[row['subject']].append(int(receipt[2]) / 1e6)
		for subject in ('base', 'cand'):
			assert len(values[subject]) == 30 and values[subject] == summary[subject]
			assert statistics.median(values[subject]) == summary[subject + '_median_ms']
		q = statistics.quantiles(values['base'], n=10)
		assert q[-1] - q[0] == summary['base_p10_p90_ms']

	regressions, disagreements = [], []
	for workload in pmu:
		di = instructions[workload]
		w = wall[workload]
		base, cand, band = w['base_median_ms'], w['cand_median_ms'], w['base_p10_p90_ms']
		dw = cand / base - 1
		if di > 0.005:
			regressions.append([workload, 'instructions', di])
		if cand - base > band:
			regressions.append([workload, 'wall', dw])
		if di * dw < 0 and abs(di) > 0.03 and abs(dw) > 0.03 and abs(cand - base) > band:
			disagreements.append([workload, di, dw])
	assert regressions == result['decision']['regressions']
	assert disagreements == result['decision']['disagreements']
	assert result['decision']['decision'] == 'STOP' and regressions
	allocation = read(root / 'allocation.json')
	assert allocation['context']['calls_delta'] == 1
	assert allocation['run-manual_next']['calls_delta'] == 1
	assert allocation['run-numeric']['calls_change'] <= -0.90
	assert all(instructions[k] <= -0.10 for k in ('run-numeric', 'run-range_signed', 'run-range_negative'))
	repro = read(root / 'base-reproduction.json')
	if profile == 'p0':
		assert len(repro) == 18
		assert all(not r['gated'] or abs(r['ratio'] - 1) <= 0.02 for r in repro.values())
	else:
		assert repro['applicable'] is False and 'not applicable' in repro['reason']
		assert not any(r['kind'].startswith('reproduction-') for r in raw)
	assert all(abs(r['difference_ms']) <= 0.15 for r in result['calibration'].values())
	assert read(root / 'sentinel-scan.json')['occurrences'] == 0
	print(json.dumps({'decision': 'STOP', 'raw_rows': len(raw),
		'kinds': dict(collections.Counter(r['kind'] for r in raw)),
		'pmu_workloads': len(pmu), 'wall_workloads': len(wall),
		'regressions': regressions, 'disagreements': disagreements,
		'numeric_allocation_change': allocation['run-numeric']['calls_change'],
		'raw_sha256': hashlib.sha256((root / 'raw.jsonl').read_bytes()).hexdigest()}, indent=2))


if __name__ == '__main__':
	main(sys.argv[1])
