"""Read-only corruption controls for the independent 0179 reconstruction; never executes a subject."""
import contextlib
import io
import json
import pathlib
import shutil
import tempfile
import sys
import audit


def main(root):
	root = pathlib.Path(root).resolve()
	results = {}
	parent = pathlib.Path(__file__).resolve().parents[2] / 'results/startup-0179'
	parent.mkdir(parents=True, exist_ok=True)
	with tempfile.TemporaryDirectory(prefix='audit-controls-', dir=parent) as temp:
		cell = pathlib.Path(temp) / 'p0-cand'
		def run(name, change=None):
			if cell.exists():
				shutil.rmtree(cell)
			cell.mkdir()
			for file in ('raw.jsonl', 'measure.json', 'pmu.json', 'wall.json', 'allocation.json',
					'base-reproduction.json', 'sentinel-scan.json', 'correctness.json'):
				shutil.copyfile(root / file, cell / file)
			if change:
				change(cell)
			try:
				with contextlib.redirect_stdout(io.StringIO()):
					audit.main(cell)
			except AssertionError:
				assert change is not None, name
				results[name] = 'refused'
			else:
				assert change is None, f'corruption accepted: {name}'
				results[name] = 'accepted'

		def raw_change(fn):
			def mutate(cell):
				file = cell / 'raw.jsonl'
				rows = [json.loads(l) for l in file.read_text().splitlines()]
				fn(rows)
				file.write_text(''.join(json.dumps(r) + '\n' for r in rows))
			return mutate

		def json_change(file, fn):
			def mutate(cell):
				path = cell / file
				d = json.loads(path.read_text())
				fn(d)
				path.write_text(json.dumps(d))
			return mutate

		run('unmodified')
		run('pmu-row-missing', raw_change(lambda rows: rows.pop(next(i for i, r in enumerate(rows) if r['kind'] == 'pmu'))))
		run('wall-row-missing', raw_change(lambda rows: rows.pop(next(i for i, r in enumerate(rows) if r['kind'] == 'wall'))))
		run('pmu-summary-forged', json_change('pmu.json', lambda d: d['context']['instructions'].__setitem__('base_median', 1)))
		run('wall-summary-forged', json_change('wall.json', lambda d: d['context'].__setitem__('base_median_ms', 1)))
		run('first-use-missing', json_change('pmu.json', lambda d: d.pop('first-use-false')))
		run('first-use-output-forged', raw_change(lambda rows: next(r for r in rows if r['kind'] == 'pmu' and r['workload'] == 'first-use-true').__setitem__('stdout', '42\n')))
		run('allocation-summary-forged', json_change('allocation.json', lambda d: d['context'].__setitem__('calls_delta', 0)))
		run('regression-list-cleared', json_change('measure.json', lambda d: d['decision'].__setitem__('regressions', [])))
		run('decision-forged-win', json_change('measure.json', lambda d: d['decision'].__setitem__('decision', 'WIN')))
		run('hash-after-forged', raw_change(lambda rows: next(r for r in rows if r.get('hash_after')).__setitem__('hash_after', '0' * 64)))
		run('non-finite-cycle-median', json_change('pmu.json', lambda d: d['context']['cycles'].__setitem__('cand_median', float('nan'))))
	print(json.dumps(results, indent=2))


if __name__ == '__main__':
	main(sys.argv[1])
