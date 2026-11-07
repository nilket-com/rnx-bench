#!/usr/bin/env python3
"""Validate the complete retained matrix and render its public tables."""
import hashlib
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'results/column-0224-summary.json'
KINDS = ('f64const', 'f64add', 'f64chain', 'booland', 'boolor', 'boolchain', 'f64gt', 'i64eq', 'f64and', 'mixedor', 'arithcmp')
LAYOUTS = ('flat', 'sliced-chunked-null', 'alternating', 'deterministic-random')
ENGINES = (('rnx', 'single'), ('arrow', 'single'), ('polars', 'single'), ('polars', 'default'), ('duckdb', 'single'), ('duckdb', 'default'))
NATIVE = set(KINDS) - {'f64const', 'f64add', 'f64chain', 'i64eq'}


def require(ok, message):
	if not ok:
		raise ValueError(message)


def main():
	raw = SOURCE.read_bytes()
	require(hashlib.sha256(raw).hexdigest() == '48fbee812f1595ed552fb7a1a92b13bccb1efdca3f5ebfc242ce972aa94563ba', 'summary identity')
	data = json.loads(raw)
	require(data['status'] == 'PASS', 'terminal status')
	index = {}
	for row in data['rows']:
		key = (row['rows'], row['layout'], row['kind'], row['engine'], row['threads'], row['panel'])
		require(key not in index, 'duplicate cell')
		index[key] = row
		require(len(row['samples']) == (5 if row['panel'] == 'equivalent' else 3), 'sample count')
		for field in ('first', 'warm'):
			values = [s[field] / 1e6 for s in row['samples']]
			require(row[field + '_ms'] == {'min': min(values), 'median': median(values), 'max': max(values)}, 'cross-process statistics')
	expected = set()
	for size in (10_000_000, 100_000_000):
		for layout in LAYOUTS:
			for kind in KINDS:
				for engine, threads in ENGINES:
					expected.add((size, layout, kind, engine, threads, 'equivalent'))
					if size == 100_000_000 and kind in NATIVE and engine in ('polars', 'duckdb'):
						expected.add((size, layout, kind, engine, threads, 'native'))
	require(set(index) == expected and len(index) == 640, 'complete matrix coverage')
	require(sum(len(r['samples']) for r in index.values()) == 2976, 'total samples')
	lines = ['# ADR 0224: complete timing matrix', '', 'Milliseconds: **median [min, max]** across independent processes. Equivalent cells use five processes; native cells use three. Warm is first reduced to the median of five calls within each process. Native semantics are not generally equivalent to rnx. A dash means not measured, not zero.', '', 'rnx and Arrow each have one serial measurement per shape; their rows apply to both thread comparisons without duplicate samples. Polars/DuckDB single = 1 thread, default = 28. See the [method and caveats](../README.md#cross-engine-column-comparison--adr-0224).', '']
	def cell(row, field):
		if row is None:
			return '—'
		v = row[field + '_ms']
		return f"{v['median']:.3f} [{v['min']:.3f}, {v['max']:.3f}]"
	for size in (10_000_000, 100_000_000):
		for layout in LAYOUTS:
			lines += [f'## {size:,} rows · {layout}', '', '| Expression key | Engine | Threads | Equivalent first | Equivalent warm | Native first | Native warm |', '|---|---|---|---:|---:|---:|---:|']
			for kind in KINDS:
				for engine, threads in ENGINES:
					key = (size, layout, kind, engine, threads)
					a, b = index[key + ('equivalent',)], index.get(key + ('native',))
					lines.append('| ' + ' | '.join([kind, engine, threads, cell(a, 'first'), cell(a, 'warm'), cell(b, 'first'), cell(b, 'warm')]) + ' |')
			lines.append('')
	(ROOT / 'results/column-0224-tables.md').write_text('\n'.join(lines))
	print('PASS: 640 cells, 2976 samples, retained sample statistics and compact source identity validated')


if __name__ == '__main__':
	main()
