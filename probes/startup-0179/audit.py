"""Independent read-only reconstruction of 0179's retained startup samples. Imports no measurement/decision code."""
import collections
import hashlib
import json
import pathlib
import math
import re
import tarfile
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
	assert all(math.isfinite(v) and v > 0 for v in values.values())
	return values


def expected_outputs():
	text = '|'.join(f'item:{i}' for i in range(1, 20001))
	values = {
		'answer': '42', 'empty': '', 'numeric': '3', 'fib': '196418',
		'strings': f'{len(text)}\n{text[:19]}\n{text[-21:]}',
		'while': str(sum(range(1, 1000001)) % 1000003),
		'compare': str(sum((i * 7) % 13 < 6 for i in range(1000000))),
		'calls': '1000000', 'vector': str(10 * sum(i % 97 for i in range(100000))),
		'overwrite_inline': str(3 * 999999), 'overwrite_mixed': str(2 * sum(range(300000))),
		'overwrite_deep': '1 2 1', 'overwrite_alias': '0 5 4 4',
		'range_signed': str(sum(range(1000000))), 'range_negative': str(sum(range(-500000, 500000))),
		'range_while': str(sum(range(1000000))),
	}
	out = {f'run-{k}': v + ('\n' if v else '') for k, v in values.items()}
	out.update({k: '' for k in ('floor', 'empty-context', 'context', 'runtime', 'compile-answer')})
	out.update({k: 'FIRST-USE 42\n' for k in ('first-use-true', 'first-use-false')})
	return out


def audit_allocations(raw, allocation):
	assert set(allocation) == set(expected_outputs()) | {'run-manual_next'}
	expected = expected_outputs()
	for label, row in allocation.items():
		for subject in ('base', 'cand'):
			matches = [r for r in raw if r['kind'] == 'allocation' and r['label'] == label and r['subject'] == subject]
			assert len(matches) == 1
			r = matches[0]
			match = re.fullmatch(r'ALLOC \[(\d+), (\d+), (\d+), (\d+)\]\n', r['stderr'])
			assert match and r['status'] == 0
			for field, val in zip(('calls', 'bytes', 'live', 'peak'), map(int, match.groups())):
				assert row[subject][field] == val
			assert row[subject]['stdout'] == r['stdout']
			want = expected.get(label, 'Some(0) Some(1) Some(2) None 4999950000\n')
			assert r['stdout'] == want
		assert row['calls_delta'] == row['cand']['calls'] - row['base']['calls']
		assert row['calls_change'] == row['cand']['calls'] / row['base']['calls'] - 1
		assert row['calls_delta'] == (0 if label in ('floor', 'empty-context') else -5801)


def audit_calibration(raw, summary):
	assert set(summary) == {'true', 'floor'}
	for name, row in summary.items():
		native = [r for r in raw if r['kind'] == 'calibration' and r['name'] == name]
		hf = [r for r in raw if r['kind'] == 'calibration-hyperfine' and r['name'] == name]
		assert len(native) == len(hf) == 1
		lines = native[0]['stdout'].splitlines()
		assert len(lines) == 300
		values = []
		for i in range(50):
			receipt = lines[i * 6:(i + 1) * 6]
			assert receipt[0] == f'EXEC {i}' and int(receipt[3]) == 0 and receipt[4] == receipt[5] == ''
			values.append(int(receipt[2]) / 1e6)
		assert statistics.median(values) == row['native_ms']
		out = hf[0]['stdout']
		assert json.loads(out[out.index('{'):])['results'][0]['median'] * 1000 == row['hyperfine_pipe_ms']
		assert row['difference_ms'] == row['native_ms'] - row['hyperfine_pipe_ms']
		assert abs(row['difference_ms']) <= 0.15


def audit_reproduction(root, raw, summary):
	repo = root.parents[3]
	with tarfile.open(repo / 'results/rune-runtime-0169-raw.tar.xz') as archive:
		data = archive.extractfile('results/rune-runtime-0169-attempt5b/counters.json').read()
	assert hashlib.sha256(data).hexdigest() == '5e09153b85afbb9b2b464039527cada2b11ee2886afa70cdc1b7bbb689279734'
	old = json.loads(data)
	data = (repo / 'results/store-fast-path-0171/run1/measure.json').read_bytes()
	assert hashlib.sha256(data).hexdigest() == 'a653251c613b68d0b2e92bcb0f6f6f57a855bc5946a2a91593fd417e6f89b986'
	ref71 = json.loads(data)['pmu']
	for key, row in summary.items():
		if key.startswith('0169 fifo '):
			mode, work = key.split()[2:]
			work = None if work == 'None' else work
			assert row['gated'] == (mode not in ('floor', 'empty-context'))
			matches = [r for r in raw if r['kind'] == 'reproduction-fifo' and r['mode'] == mode and r['work'] == work]
			assert [r['index'] for r in matches] == [0, 1, 2]
			vals = [counters(r['counter_raw'])['instructions'] for r in matches]
			ref = [r['counts']['instructions'] for r in old if r['base'] == 'new' and r['mode'] == mode and r['work'] == work]
		else:
			assert key.startswith('0171 whole-process run ')
			assert row['gated'] is True
			work = key.split()[-1]
			matches = [r for r in raw if r['kind'] == 'reproduction-pmu' and r['work'] == work]
			assert [r['index'] for r in matches] == [0, 1, 2]
			vals = [counters(r['stderr'])['instructions'] for r in matches]
			ref = ref71[f'base-{work}']['instructions']
		assert vals == row['samples'] and statistics.median(vals) == row['median']
		assert statistics.median(ref) == row['reference']
		assert row['ratio'] == row['median'] / row['reference']


def main(root):
	root = pathlib.Path(root)
	raw = [json.loads(line) for line in (root / 'raw.jsonl').read_text().splitlines()]
	result, pmu, wall = (read(root / name) for name in ('measure.json', 'pmu.json', 'wall.json'))
	profile, source = root.name.split('-')
	assert profile == 'p0' and source == 'cand'
	roles = {'base': profile + '-base', 'cand': profile + '-' + source}
	assert result['pair'] == {'profile': profile, 'source': source, 'roles': roles}
	expected = expected_outputs()
	assert set(pmu) == set(wall) == set(expected)
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
		assert all(r['status'] == 0 and r['stdout'] == expected[workload] for r in rows)
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
				assert bytes.fromhex(receipt[4]).decode() == expected[workload]
				assert bytes.fromhex(receipt[5]) == b''
				assert int(receipt[2]) > 0
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
		assert result['decision']['rows'][workload] == {
			'base_instr': pmu[workload]['instructions']['base_median'],
			'cand_instr': pmu[workload]['instructions']['cand_median'],
			'instr_change': di, 'base_wall_ms': base, 'cand_wall_ms': cand,
			'wall_change': dw, 'base_wall_p10_p90_ms': band,
		}
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
	audit_allocations(raw, allocation)
	assert all(instructions[k] > -0.10 for k in ('context', 'run-answer'))
	assert result['decision']['win_instr'] == {k: instructions[k] for k in ('context', 'run-answer')}
	assert result['decision']['context_alloc_delta'] == allocation['context']['calls_delta']
	repro = read(root / 'base-reproduction.json')
	if profile == 'p0':
		assert len(repro) == 18
		assert all(not r['gated'] or abs(r['ratio'] - 1) <= 0.02 for r in repro.values())
	else:
		assert repro['applicable'] is False and 'not applicable' in repro['reason']
		assert not any(r['kind'].startswith('reproduction-') for r in raw)
	audit_reproduction(root, raw, repro)
	audit_calibration(raw, result['calibration'])
	assert len(read(root / 'correctness.json')) == 42
	assert all(v['same'] and v.get('oracle') is not False for v in read(root / 'correctness.json').values())
	assert read(root / 'sentinel-scan.json')['occurrences'] == 0
	print(json.dumps({'decision': 'STOP', 'raw_rows': len(raw),
		'kinds': dict(collections.Counter(r['kind'] for r in raw)),
		'pmu_workloads': len(pmu), 'wall_workloads': len(wall),
		'regressions': regressions, 'disagreements': disagreements,
		'context_allocation_delta': allocation['context']['calls_delta'],
		'context_instructions_change': instructions['context'],
		'run_answer_instructions_change': instructions['run-answer'],
		'first_use_instructions_change': {k: instructions[k] for k in ('first-use-true', 'first-use-false')},
		'without_regressions': 'NO-WIN',
		'raw_sha256': hashlib.sha256((root / 'raw.jsonl').read_bytes()).hexdigest()}, indent=2))


if __name__ == '__main__':
	main(sys.argv[1])
