"""Validate archived column evidence and render tables without running benchmarks."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'results/column-0205-2026-11-04'
REPORT = ROOT / 'results/column-0205-2026-11-04.md'
KINDS = ('i64add', 'axpy', 'boolnot', 'f64add', 'multiply3')
SIZES = (10_000_000, 100_000_000)
LAYOUTS = ('flat', 'sliced-chunked-null')
MODES = ('auto', 'portable', 'reference', 'polars')
LABELS = {'i64add': 'checked x+1', 'axpy': 'checked x*2+y', 'boolnot': 'packed !x', 'f64add': 'F64 x+y', 'multiply3': 'checked x*3+y', 'auto': 'Rune host AVX2', 'portable': 'Rune host portable', 'reference': 'Rune per-row', 'polars': 'Polars py-2.1.0'}


def sha(data):
	return hashlib.sha256(data).hexdigest()


def validate(cli, matched, allocation, provenance):
	assert cli['status'] == matched['status'] == provenance['acceptance'] == 'PASS'
	assert provenance['rnx'] == 'bc0fada750c6fa50f2b0e765a2985155bd933e00'
	assert provenance['rune'] == '1b4b66bd3657868ecb1d49f8b3f355585b3ec98d'
	assert provenance['polars'] == '7f902bd3ffd27ff82d14278a09a295ff2f7aed92'
	assert cli['binary_sha256'] == provenance['binaries']['cli']
	assert provenance['existing_path']['raw_status'] == 'FAIL'
	assert provenance['existing_path']['reviewed_status'] == 'ACCEPTED_ATTRIBUTED'
	assert provenance['identity']['whole_binary_identical'] is False
	for name in ('.text', '.rodata'):
		assert provenance['identity']['sections'][name]['size'] > 0
		assert re.fullmatch('[0-9a-f]{64}', provenance['identity']['sections'][name]['sha256'])
	keys = [(r['kind'], r['rows'], r['layout']) for r in cli['cases']]
	assert len(keys) == len(set(keys)) == 20
	assert set(keys) == set(itertools.product(KINDS, SIZES, LAYOUTS))
	for r in cli['cases']:
		assert r['direct_exit'] == r['profile_exit'] == 0 and r['budget'] == 1_000_000_000
		assert r['timing_resolution_ms'] == 1
		assert len(r['profiles']) == len(r['observations']) == len(r['map_elapsed_ms']) == 2
		g = r['gdb']
		assert g['status'] == 'PASS' and g['exit'] == 0 and not g['errors']
		assert g['entries'] == g['returns'] == [1, 1] and len(g['workers']) == 2
		path = 'avx2' if r['kind'] in ('i64add', 'axpy') or (r['kind'] == 'boolnot' and r['layout'] == 'flat') else 'scalar-primitives'
		for i, observation in enumerate(r['observations']):
			assert observation['call'] == i and observation['completed']
			assert observation['path'] == path and observation['rows'] == r['rows']
			assert observation['valid_rows'] == r['rows'] // (1 if r['layout'] == 'flat' else 2)
			assert observation['attempts'] == 1 and observation['replays'] == 0 and observation['refusal'] == 'None'
			assert observation['ms'] == r['map_elapsed_ms'][i] >= 0
			assert r['profiles'][i]['Ir'] > 0
	keys = [(r['mode'], r['rows'], r['profiled']) for r in matched['records']]
	assert len(keys) == len(set(keys)) == 16
	assert set(keys) == set(itertools.product(MODES, SIZES, (False, True)))
	checksums = {}
	for r in matched['records']:
		d = r['data']; assert d['status'] == 'PASS' and d['rows'] == r['rows']
		samples = [d] if r['mode'] == 'polars' else d['samples']
		assert len(samples) == (1 if r['mode'] == 'polars' else 2)
		if not r['profiled']:
			assert r['thermal_stable'], 'invalid direct timing must not become a headline'
		for s in samples:
			checksums.setdefault(r['rows'], s['checksum'])
			assert s['checksum'] == checksums[r['rows']], 'complete-output checksums disagree'
			if r['mode'] != 'polars':
				assert s['path'] == {'auto': 'Some(Avx2)', 'portable': 'Some(ScalarPrimitives)', 'reference': 'Some(ScalarFallback)'}[r['mode']]
				assert s['output_capacity_bytes'] == r['rows'] * 8
			if not r['profiled']:
				assert s['cycles_valid'] and s['pmu_enabled'] == s['pmu_running'] > 0
		assert len(r['profiles']) == (len(samples) if r['profiled'] else 0)
		for i, profile in enumerate(r['profiles']):
			assert profile['call'] == i and profile['Ir'] > 0
			assert abs(profile['Ir_per_row'] - profile['Ir'] / r['rows']) < 1e-10
	assert len(allocation) == 2 and {r['rows'] for r in allocation} == set(SIZES)
	for r in allocation:
		assert not r['auto']['scalar_entry_functions'] and r['auto']['malloc_calls'] == 8
		assert r['auto']['kernel_blocks'] == (r['rows'] + 1023) // 1024
		for symbol in ('<rnx::column::scalar::Engine>::call', '<rune::experimental_core::execute::Executor>::invoke'):
			assert r['reference']['scalar_entry_functions'][symbol]['calls'] == r['rows']


def load():
	manifest = json.loads((ARCHIVE / 'MANIFEST.json').read_text())
	for name, digest in manifest['files'].items():
		path = ROOT / name
		assert path.resolve().is_relative_to(ROOT)
		data = path.read_bytes()
		assert sha(data) == digest, f'archive changed: {name}'
		assert len(data) < 1_000_000
		assert (b'/' + b'home/') not in data, name
	proof = json.loads((ARCHIVE / 'formatting-proof.json').read_text())
	assert proof['status'] == 'PASS' and len(proof['files']) == 3
	harness = {r['archive']: r for r in json.loads((ARCHIVE / 'harness.json').read_text())}
	for row in proof['files']:
		data = (ROOT / row['archive']).read_bytes()
		assert row['diff_w_empty'] and row['expandtabs_4_reconstructs_pre_tab_bytes']
		assert sha(data) == row['post_tab_archive_sha256'] == harness[row['archive']]['archived_sha256']
		assert sha(data.expandtabs(4)) == row['pre_tab_archive_sha256'], 'formatting changed non-whitespace bytes'
		assert row['measured_sha256'] == harness[row['archive']]['original_sha256']
	objects = [json.loads((ARCHIVE / (name + '.json')).read_text()) for name in ('cli', 'matched', 'allocation', 'provenance')]
	validate(*objects)
	text = (ROOT / 'README.md').read_text()
	old_matrix = text.split('<!-- current-matrix:start -->')[1].split('<!-- current-matrix:end -->')[0]
	assert sha(old_matrix.encode()) == objects[3]['preserved_n6_matrix_sha256'], 'historical matrix changed'
	return objects


def tables(cli, matched):
	index = {(r['mode'], r['rows'], r['profiled']): r for r in matched['records']}
	head = ['| Mode | Rows | Prepare ms | First ms | Warm ms | Warm Ir/row | Warm user cycles/row | Logical GB/s |', '|---|---:|---:|---:|---:|---:|---:|---:|']
	for n in SIZES:
		for mode in MODES:
			d = index[mode, n, False]['data']; ir = index[mode, n, True]['profiles'][-1]['Ir'] / n
			if mode == 'polars':
				prep = first = '—'; ns = d['measured_ns']; cycles = d['cycles']
			else:
				prep = f"{d['prepare_ns'] / 1e6:.3f}"; first = f"{d['samples'][0]['elapsed_ns'] / 1e6:.3f}"
				ns = d['samples'][1]['elapsed_ns']; cycles = d['samples'][1]['cycles_raw']
			head.append(f'| {LABELS[mode]} | {n // 1_000_000}M | {prep} | {first} | {ns / 1e6:.3f} | {ir:.8f} | {cycles / n:.3f} | {16 * n / ns:.3f} |')
	def ms(r, i):
		return 'unavailable †' if not r['thermal_stable'] else ('<1' if r['map_elapsed_ms'][i] == 0 else str(r['map_elapsed_ms'][i]))
	matrix = ['| Kernel | Rows | Layout | Path | First Ir/row | Warm Ir/row | First ms | Warm ms |', '|---|---:|---|---|---:|---:|---:|---:|']
	for r in sorted(cli['cases'], key=lambda r: (r['rows'], KINDS.index(r['kind']), LAYOUTS.index(r['layout']))):
		n = r['rows']; a, b = r['profiles']
		matrix.append(f"| {LABELS[r['kind']]} | {n // 1_000_000}M | {r['layout']} | {r['observations'][0]['path']} | {a['Ir'] / n:.8f} | {b['Ir'] / n:.8f} | {ms(r, 0)} | {ms(r, 1)} |")
	auto = index['auto', 100_000_000, False]['data']['samples'][1]['elapsed_ns']
	ref = index['reference', 100_000_000, False]['data']['samples'][1]['elapsed_ns']
	polars = index['polars', 100_000_000, False]['data']['measured_ns']
	ratio = f'On these warm measurements, Rune host AVX2 is {ref / auto:.2f}× faster than per-row Rune; Polars is {auto / polars:.2f}× faster than Rune host AVX2. These are ratios of individual measured calls, not statistical rankings.'
	return '\n'.join(head), '\n'.join(matrix), ratio


def replace(text, marker, value):
	start = f'<!-- {marker}:start -->'; end = f'<!-- {marker}:end -->'
	assert text.count(start) == text.count(end) == 1
	a, rest = text.split(start); _, b = rest.split(end)
	return a + start + '\n\n' + value + '\n\n' + end + b


def overview(cli, matched):
	index = {(r['mode'], r['rows'], r['profiled']): r for r in matched['records']}
	n = 100_000_000
	lines = ['Published **rnx 0205 `bc0fada` / Rune `1b4b66bd`** adds the explicit',
		'`polars::column_kernel(...).map(...)` path for borrowed numeric/Boolean columns.',
		'The following warm `x + 1` measurements process **100 million non-null i64 rows**',
		'and include output allocation. Input construction and validation are outside',
		'the interval. These are individual calls, not repeated-sample means.', '',
		'| Path | Warm ms | Instructions/row |', '|---|---:|---:|']
	r = next(r for r in cli['cases'] if (r['kind'], r['rows'], r['layout']) == ('i64add', n, 'flat'))
	assert r['thermal_stable']
	lines.append(f"| Actual Rune CLI map | {r['map_elapsed_ms'][1]} | {r['profiles'][1]['Ir'] / n:.3f} |")
	for mode in ('auto', 'reference', 'polars'):
		d = index[mode, n, False]['data']
		ns = d['measured_ns'] if mode == 'polars' else d['samples'][1]['elapsed_ns']
		ir = index[mode, n, True]['profiles'][-1]['Ir'] / n
		lines.append(f'| {LABELS[mode]} | {ns / 1e6:.3f} | {ir:.3f} |')
	lines += ['', tables(cli, matched)[2], '',
		'The matched host/Polars comparison uses varied inputs; the CLI uses constant',
		'inputs and includes Arrow adaptation and the worker join. Host timing excludes',
		'Arrow wrapping/output destruction; Polars eager assignment includes dropping',
		'the prior output. Polars wraps integers, while Rune checks overflow; these inputs',
		'do not overflow. Build recipes differ. No one-instruction-per-row claim is made.', '',
		'The full report includes 10M/100M first and warm calls, preparation, all twenty',
		'CLI cases, selected paths, null/slice/chunk costs, allocation proofs and thermal',
		'exclusions. Large CLI cases set `--budget 1000000000`; the default remains',
		'2,000,000. User-cycle counts exclude kernel page-fault time. Existing-path',
		'publication includes three explicitly attributed performance exceptions.', '',
		'[Results, limits and archived evidence](results/column-0205-2026-11-04.md).',
		'The older whole-process N6 matrix below retains its original binary and numbers.']
	return '\n'.join(lines)


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument('--check', action='store_true')
	args = parser.parse_args()
	cli, matched, _, _ = load()
	head, matrix, ratio = tables(cli, matched)
	original = REPORT.read_text()
	rendered = replace(replace(replace(original, 'column-headline', head), 'column-cli', matrix), 'column-ratios', ratio)
	readme_path = ROOT / 'README.md'
	readme = readme_path.read_text()
	updated = replace(readme, 'column-summary', overview(cli, matched))
	if args.check:
		assert original == rendered, 'report needs rendering'
		assert readme == updated, 'README needs rendering'
	else:
		REPORT.write_text(rendered)
		readme_path.write_text(updated)
	print('PASS', REPORT.relative_to(ROOT))


if __name__ == '__main__':
	main()
