"""Report-only matched x+1 comparison; exact sizes, complete output validation, pinned binaries."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
import subprocess

HERE = Path(__file__).resolve().parent
sys.path.insert(0, '<RUNE_ROOT>/tools/xtask/measure')
import callgrind
import measurement_runtime as runtime
import measurement_readiness as readiness

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--mode', choices=('preflight', 'full'), required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=False)
polars = Path('<POLARS_PROBE>')
vgroot = Path('<VALGRIND_ROOT>')
started = time.monotonic()
result = {'status': 'FAIL', 'mode': args.mode, 'records': []}
pins = {}

def sha(path):
	return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def exact():
	for path, digest in pins.items():
		assert sha(path) == digest, path

def ready(lease, path):
	original = readiness.require_ready
	def recorded(observation, **limits):
		path.write_text(json.dumps({'observation': observation, 'limits': limits}, indent=2) + '\n')
		return original(observation, **limits)
	readiness.require_ready = recorded
	try:
		return lease.ready(max_load=2, min_available_bytes=8*1024**3)
	finally:
		readiness.require_ready = original

try:
	validation = json.loads((HERE / 'validation-v1/RESULT.json').read_text())
	assert validation['status'] == 'PASS'
	binaries = {'host': Path(validation['binary']), 'polars': polars / 'target/release/column-polars21-step0'}
	assert sha(binaries['host']) == validation['binary_sha256']
	assert '7f902bd3ffd27ff82d14278a09a295ff2f7aed92' in (polars / 'Cargo.lock').read_text()
	for base in (HERE, polars):
		for path in [base / 'Cargo.toml', base / 'Cargo.lock', base / 'build.rs', base / 'measure.c', *sorted((base / 'src').glob('*.rs'))]:
			pins[str(path)] = sha(path)
	for path in [*binaries.values(), Path(__file__), HERE / 'validation-v1/RESULT.json']:
		pins[str(path)] = sha(path)
	result.update(pins=pins, host_source_commit=validation['source_commit'], polars_revision='7f902bd3ffd27ff82d14278a09a295ff2f7aed92',
		dependencies=runtime.dependency_snapshot([*binaries.values(), vgroot / 'bin/valgrind']), profiler=runtime.tool_tree(vgroot),
		scope='Host map vs eager Polars x+1 on identical nonnull i64 data (i%1009)-500; output allocation included. Host excludes Arrow wrapper and output destruction; Polars warm assignment also drops previous output. Input preparation and complete validation excluded. Polars wraps overflow; values chosen never overflow. Actual CLI headline is a separate existing capture.',
		recipe_note='Host comparator uses its recorded Cargo release profile; Polars21 comparator uses recorded opt3/CGU1/no-LTO profile. This is report-only, not a same-recipe performance gate.')
	if args.mode == 'full':
		preflight = HERE / 'measurement-preflight-v1/RESULT.json'
		prior = json.loads(preflight.read_text())
		assert prior['status'] == 'PASS' and prior['pins'] == pins
		result['preflight_sha256'] = sha(preflight)
	deadline = time.monotonic() + 36000
	env = {'PATH': '<USER_HOME>/.cargo/bin:/usr/local/bin:/usr/bin:/bin', 'HOME': '<USER_HOME>', 'LANG': 'C', 'LC_ALL': 'C', 'POLARS_MAX_THREADS': '1'}
	checksums = {}
	time.sleep(180)
	with runtime.lease('/tmp/rnx-runtime-bench.lock', 2) as lease:
		for n in ([4096] if args.mode == 'preflight' else [10_000_000, 100_000_000]):
			for mode in ('auto', 'portable', 'reference', 'polars'):
				key = 'polars' if mode == 'polars' else 'host'
				command = [str(binaries[key]), *(['polars', 'i64add', str(n), '2', '1', '-'] if key == 'polars' else [mode, str(n)])]
				for profiled in (False, True):
					exact()
					name = f'{mode}-{n}-' + ('ir' if profiled else 'time')
					case = out / name
					case.mkdir()
					argv = command
					if profiled:
						argv = [str(vgroot / 'bin/valgrind'), '--tool=callgrind', '--instr-atstart=no', '--collect-jumps=yes', '--dump-instr=yes', '--cache-sim=no', '--branch-sim=no', '--callgrind-out-file=' + str(case / 'phase.callgrind'), *command]
					before = ready(lease, case / 'READY.json')
					execution = lease.execute(argv, cwd=HERE, env=env, stdout_path=case / 'program.stdout', stderr_path=case / 'program.stderr', timeout=10800, deadline=deadline)
					after = readiness.snapshot(2)
					execution.update(readiness=before, post_observation=after, thermal_stable=before['observation']['core_throttle_count'] == after['core_throttle_count'])
					(case / 'EXECUTION.json').write_text(json.dumps(execution, indent=2) + '\n')
					assert execution['status'] == 0, name
					data = json.loads((case / 'program.stdout').read_text())
					assert data['status'] == 'PASS' and data['rows'] == n
					samples = data['samples'] if key == 'host' else [data]
					assert len(samples) == (2 if key == 'host' else 1)
					for sample in samples:
						checksums.setdefault(n, sample['checksum'])
						assert sample['checksum'] == checksums[n], 'cross-runtime full-output checksum mismatch'
						if key == 'host':
							assert sample['path'] == {'auto': 'Some(Avx2)', 'portable': 'Some(ScalarPrimitives)', 'reference': 'Some(ScalarFallback)'}[mode]
						if not profiled:
							sample['cycles_valid'] = sample['pmu_enabled'] > 0 and sample['pmu_running'] == sample['pmu_enabled'] and execution['thermal_stable']
					row = {'mode': mode, 'rows': n, 'profiled': profiled, 'data': data, 'thermal_stable': execution['thermal_stable'], 'profiles': []}
					if profiled:
						parts = sorted(case.glob('phase.callgrind.*'))
						assert len(parts) == len(samples), (name, len(parts))
						for index, path in enumerate(parts):
							parsed = callgrind.parse(path)
							assert parsed['total_Ir'] > 0
							row['profiles'].append({'call': index, 'file': str(path), 'sha256': sha(path), 'Ir': parsed['total_Ir'], 'Ir_per_row': parsed['total_Ir'] / n})
					(case / 'CAPTURE.json').write_text(json.dumps(row, indent=2) + '\n')
					result['records'].append(str(case / 'CAPTURE.json'))
					exact()
					time.sleep(5)
	result['status'] = 'PASS'
except BaseException as error:
	result['error'] = repr(error)
	(out / 'TRACEBACK.txt').write_text(traceback.format_exc())
finally:
	result['seconds'] = time.monotonic() - started
	(out / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
	summary = '0205 headline matched comparison ' + args.mode + ' EXIT ' + result['status']
	notice = out / 'NOTICE.txt'
	notice.write_text(summary + '. Receipt: ' + str(out / 'RESULT.json') + '\n')
	subprocess.run(['chatctl', 'send', '--as', 'sluice', '--to', 'codex', '--conversation', 'rune-native', '--summary', summary, '--body-file', str(notice)], check=True)
raise SystemExit(0 if result['status'] == 'PASS' else 1)
