"""0180 retained-file analysis. Never invokes an experiment subject or compiler."""
import argparse
import hashlib
import json
import math
import pathlib
import re
import shutil
import os
import signal
import statistics
import subprocess
import time

MANIFEST = 'd3552638c3e0fbc8d9cfe538a3488a35edf0d432454b6c4e9d1359363e1fd8a1'
RAW = 'd0643c0fc1ca42f6c4e9e5d9748c351da546b0baed3d1226349d6e5fab848b03'
ENV = {'PATH': '/usr/bin:/bin', 'HOME': '/home/me', 'LANG': 'C.UTF-8'}
SURFACE = re.compile(r'rune::runtime::vm::Vm::(?:run|op_call|pop_call_frame)|RangeIter|rune::runtime::value::|drop_glue.*(?:Value|Repr)|rune::modules::(?:iter|ops)::.*(?:next|range)')
PREDICTIONS = {
	'run-numeric': ('corpus/numeric.rn', 1000000, -12),
	'run-range_signed': ('range/range_signed.rn', 1000000, -10),
	'run-range_negative': ('range/range_negative.rn', 1000000, -10),
	'run-while': ('fixtures/while.rn', 1000000, -7),
	'run-range_while': ('range/range_while.rn', 1000000, -5),
	'run-overwrite_inline': ('fixtures/overwrite_inline.rn', 1000000, -38),
	'run-calls': ('fixtures/calls.rn', 1000000, 10),
}


def sha(data):
	return hashlib.sha256(data).hexdigest()


def require(test, message):
	if not test:
		raise ValueError(message)


def dump(path, data):
	path.write_text(json.dumps(data, indent=1, allow_nan=False) + '\n')


def counter_values(text):
	out = {}
	for line in text.splitlines():
		if not line.startswith('{'):
			continue
		r = json.loads(line)
		for key in ('instructions', 'cycles'):
			if r.get('event') in (key + ':u', 'cpu_core/' + key + '/u'):
				require(key not in out, 'duplicate event')
				x = float(r['counter-value'])
				require(math.isfinite(x) and x > 0, 'invalid count')
				require(99 <= float(r['pcnt-running']) <= 100, 'counter scheduling')
				out[key] = x
	require(set(out) == {'instructions', 'cycles'}, 'missing event')
	return out


def arithmetic(repo, manifest, out):
	root = repo / 'results/startup-0179/official1/p0-cand'
	data = (root / 'raw.jsonl').read_bytes()
	require(sha(data) == RAW, 'raw hash')
	raw = [json.loads(x) for x in data.decode().splitlines()]
	pmu = json.loads((root / 'pmu.json').read_text())
	medians = {}
	for work in pmu:
		rows = [r for r in raw if r['kind'] == 'pmu' and r['workload'] == work]
		require(len(rows) == 20, 'PMU row count')
		for rep in range(5):
			require([r['subject'] for r in rows if r['rep'] == rep] == ['base', 'cand', 'cand', 'base'], 'ABBA order')
		m = {}
		for side in ('base', 'cand'):
			rs = [r for r in rows if r['subject'] == side]
			for r in rs:
				require(r['hash'] == manifest['binaries'][f'p0-{side}-primary'], 'PMU role/hash')
				require(r['status'] == 0 and r['reaped'] and not r['group_survivors'], 'PMU lifecycle')
				counter_values(r['stderr'])
			for event in ('instructions', 'cycles'):
				vals = [counter_values(r['stderr'])[event] for r in rs]
				require(vals == pmu[work][event][side], 'retained PMU samples')
				m[side + '_' + event] = statistics.median(vals)
				require(m[side + '_' + event] == pmu[work][event][side + '_median'], 'retained median')
		m['instruction_delta'] = m['cand_instructions'] - m['base_instructions']
		m['cycle_change'] = m['cand_cycles'] / m['base_cycles'] - 1
		medians[work] = m
	startup = medians['run-empty']['instruction_delta']
	checks = {}
	for work, (script, count, predicted) in PREDICTIONS.items():
		data = (repo / 'probes/startup-0179' / script).read_bytes()
		require(sha(data) == manifest['inputs'][script], 'script hash ' + script)
		adjusted = medians[work]['instruction_delta'] - startup
		checks[work] = {
			'script': script, 'sha256': sha(data), 'source': data.decode(),
			'operation_count': count, 'count_basis': 'source-bound fixed one-million loop; inspect frozen source below',
			'adjusted_delta': adjusted, 'prediction_per_operation': predicted,
			'per_operation': adjusted / count, 'residue': adjusted - predicted * count,
		}
	fibscript = 'corpus/fib.rn'
	data = (repo / 'probes/startup-0179' / fibscript).read_bytes()
	require(sha(data) == manifest['inputs'][fibscript], 'fib script hash')
	calls = [1, 1]
	for n in range(2, 28):
		calls.append(1 + calls[-1] + calls[-2])
	checks['run-fib'] = {
		'script': fibscript, 'sha256': sha(data), 'source': data.decode(),
		'count_basis': 'F(0)=F(1)=1; F(n)=1+F(n-1)+F(n-2); includes root fib(27), excludes main',
		'fib_invocations': calls[27], 'nonleaf_invocations': (calls[27] - 1) // 2,
		'adjusted_delta': medians['run-fib']['instruction_delta'] - startup,
		'per_invocation': (medians['run-fib']['instruction_delta'] - startup) / calls[27],
		'warning': 'no fixed per-fib-call prediction accepted; leaf and nonleaf paths differ',
	}
	dump(out / 'arithmetic.json', {'raw_sha256': RAW, 'medians': medians, 'run_empty_delta': startup, 'contrasts': checks,
		'scope': 'difference of retained whole-process medians, not a measured phase; setup/compiler differences remain'})


def symbols(text):
	out = {}
	for line in text.splitlines():
		m = re.fullmatch(r'([0-9a-f]+) ([0-9a-f]+) ([tT]) (.+)', line)
		if m:
			a, size = int(m[1], 16), int(m[2], 16)
			out.setdefault((a, size), []).append(m[4])
	require(bool(out), 'no text symbols')
	return out


def disassembly(text):
	blocks = {}
	current = None
	for line in text.splitlines():
		m = re.fullmatch(r'([0-9a-f]+) <(.+)>:', line)
		if m:
			current = int(m[1], 16)
			require(current not in blocks, 'duplicate disassembly address')
			blocks[current] = {'name': m[2], 'instructions': []}
			continue
		m = re.match(r'\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )*[0-9a-f]{2})\s+(.+)', line)
		if m and current is not None:
			bs = bytes.fromhex(m[2])
			asm = m[3].strip()
			parts = asm.split(None, 1)
			blocks[current]['instructions'].append({'address': int(m[1], 16), 'bytes': bs.hex(), 'length': len(bs),
				'op': parts[0], 'operand': parts[1] if len(parts) > 1 else ''})
	return blocks


def validate_region(a, size, block):
	xs = block['instructions']
	require(size > 0 and bool(xs) and xs[0]['address'] == a, 'missing region instructions')
	pos = a
	for x in xs:
		if x['address'] >= a + size:
			break
		require(x['address'] == pos, 'truncated/noncontiguous disassembly')
		pos += x['length']
	require(pos == a + size, 'incomplete symbol extent')
	return [x for x in xs if x['address'] < a + size]


def normalized(xs, a, size, targets):
	out = []
	for x in xs:
		op, operand = x['op'], x['operand']
		if op.startswith('j') or op in ('call', 'callq'):
			m = re.fullmatch(r'([0-9a-f]+) <([^>]+)>', operand)
			if m:
				t = int(m[1], 16)
				if a <= t < a + size:
					operand = f'local+{t-a:x}'
				else:
					names = targets.get(t, [])
					require(bool(names), 'unresolved direct target')
					operand = 'target:' + '|'.join(sorted(names))
		out.append([op, operand])
	return out


def boundary_rows(xs, a):
	starts = {a}
	for x in xs:
		m = re.fullmatch(r'([0-9a-f]+) <([^>]+)>', x['operand'])
		if x['op'].startswith('j') and m:
			starts.add(int(m[1], 16))
			starts.add(x['address'] + x['length'])
	return {'block_candidates': [{'address': b, 'offset': b-a, 'mod16': b%16, 'mod32': b%32, 'mod64': b%64}
		for b in sorted(starts) if a <= b <= xs[-1]['address']],
		'instruction_crossings': {str(n): [x['address'] for x in xs if x['address']//n != (x['address']+x['length']-1)//n] for n in (16,32,64)}}


def command(argv, path, ledger):
	tool = pathlib.Path(shutil.which(argv[0])).resolve()
	started = time.time()
	p = subprocess.Popen(argv, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
	timed_out = False
	try:
		stdout, stderr = p.communicate(timeout=120)
	except subprocess.TimeoutExpired:
		timed_out = True
		os.killpg(p.pid, signal.SIGKILL)
		stdout, stderr = p.communicate(timeout=5)
	path.write_bytes(stdout)
	path.with_suffix(path.suffix + '.stderr').write_bytes(stderr)
	ledger.append({'argv': argv, 'tool': str(tool), 'tool_sha256': sha(tool.read_bytes()), 'env': ENV,
		'started': started, 'exit': p.returncode, 'timed_out': timed_out, 'reaped': p.returncode is not None, 'stdout_sha256': sha(stdout), 'stderr_sha256': sha(stderr)})
	require(not timed_out and p.returncode == 0, 'tool failed: ' + argv[0])
	return stdout.decode()


def extract(binary, prefix, out, ledger):
	nm = command(['nm', '-S', '-n', '--defined-only', str(binary)], out / (prefix + '.nm'), ledger)
	dem = command(['nm', '-S', '-n', '-C', '--defined-only', str(binary)], out / (prefix + '.demangled.nm'), ledger)
	txt = command(['objdump', '-d', '-w', str(binary)], out / (prefix + '.asm'), ledger)
	command(['readelf', '-W', '-a', str(binary)], out / (prefix + '.elf'), ledger)
	raw, human, blocks = symbols(nm), symbols(dem), disassembly(txt)
	targets = {}
	for (a, size), names in raw.items():
		targets.setdefault(a, []).extend(names)
	regions = []
	for (a, size), names in human.items():
		if not size or not any(SURFACE.search(n) for n in names):
			continue
		require((a, size) in raw and a in blocks, 'selected region missing')
		xs = validate_region(a, size, blocks[a])
		row = {'address': a, 'size': size, 'raw_names': raw[a, size], 'demangled_names': names,
			'bytes_sha256': sha(bytes.fromhex(''.join(x['bytes'] for x in xs))), 'instructions': xs,
			'boundaries': boundary_rows(xs, a)}
		try:
			row['normalized'] = normalized(xs, a, size, targets)
		except ValueError as e:
			row['normalization_unresolved'] = str(e)
		regions.append(row)
	require(any('Vm::run' in n for r in regions for n in r['demangled_names']), 'Vm::run absent')
	dump(out / (prefix + '.regions.json'), regions)
	return regions


def compare(left, right):
	def index(rows):
		out = {}
		for r in rows:
			for name in r['demangled_names']:
				out.setdefault(name, []).append(r)
		return out
	l, r = index(left), index(right)
	out = []
	for name in sorted(set(l) | set(r)):
		x, y = l.get(name, []), r.get(name, [])
		row = {'name': name, 'base_extents': [[v['address'], v['size']] for v in x], 'cand_extents': [[v['address'], v['size']] for v in y]}
		if len(x) != 1 or len(y) != 1:
			row['classification'] = 'unresolved identity or absent standalone region'
		elif 'normalized' not in x[0] or 'normalized' not in y[0]:
			row['classification'] = 'unresolved target normalization'
		else:
			row['classification'] = 'equivalent inspected sequence' if x[0]['normalized'] == y[0]['normalized'] else 'changed inspected sequence'
			row['base_instructions'] = len(x[0]['instructions'])
			row['cand_instructions'] = len(y[0]['instructions'])
			row['bytes_equal'] = x[0]['bytes_sha256'] == y[0]['bytes_sha256']
		out.append(row)
	return out


def main():
	p = argparse.ArgumentParser()
	p.add_argument('repo', type=pathlib.Path)
	p.add_argument('bin', type=pathlib.Path)
	p.add_argument('out', type=pathlib.Path)
	a = p.parse_args()
	require(not a.out.exists(), 'output exists')
	a.out.mkdir(parents=True)
	ledger = []
	try:
		data = (a.repo / 'probes/startup-0179/subjects.json').read_bytes()
		require(sha(data) == MANIFEST, 'manifest hash')
		m = json.loads(data)
		for role, want in m['binaries'].items():
			require(sha((a.bin / role).read_bytes()) == want, 'binary hash: ' + role)
		arithmetic(a.repo, m, a.out)
		for tool in ('nm', 'objdump', 'readelf'):
			command([tool, '--version'], a.out / (tool + '.version'), ledger)
		for role in ('primary', 'counter'):
			rows = [extract(a.bin / f'p0-{side}-{role}', f'{side}-{role}', a.out, ledger) for side in ('base', 'cand')]
			dump(a.out / (role + '.comparison.json'), compare(*rows))
		dump(a.out / 'completed.json', {'completed': True, 'scope': 'static files only; primary deciding, counter secondary',
			'source_sha256': sha(pathlib.Path(__file__).read_bytes()), 'manifest_sha256': MANIFEST, 'raw_sha256': RAW})
	finally:
		dump(a.out / 'ledger.json', ledger)


if __name__ == '__main__':
	main()
