"""Render the published 0206 measurements from compact, hash-checked evidence."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'results/column-0206-2026-11-05'
REPORT = ROOT / 'results/column-0206-2026-11-05.md'
KINDS = ('i64add', 'axpy', 'multiply3', 'f64const', 'f64add', 'boolnot')
LAYOUTS = ('flat', 'alternating', 'deterministic-random', 'sliced-chunked-null')
LABELS = dict(i64add='checked x+1', axpy='checked x*2+y', multiply3='checked x*3+y', f64const='F64 x+1.0', f64add='F64 x+y', boolnot='packed !x')


def load():
	manifest = json.loads((ARCHIVE / 'MANIFEST.json').read_text())
	assert set(manifest['files']) == {'matrix.json', 'timing.json', 'provenance.json'}
	for name, digest in manifest['files'].items():
		data = (ARCHIVE / name).read_bytes()
		assert hashlib.sha256(data).hexdigest() == digest, name
		assert len(data) < 1_000_000 and b'/home/' not in data
	matrix = json.loads((ARCHIVE / 'matrix.json').read_text())
	keys = [(r['kind'], r['rows'], r['layout'], r['role']) for r in matrix]
	assert len(keys) == len(set(keys)) == 96
	assert set(keys) == set(itertools.product(KINDS, (10_000_000, 100_000_000), LAYOUTS, ('baseline', 'candidate')))
	for r in matrix:
		assert len(r['calls']) == 2
		for c in r['calls']:
			assert c['Ir'] == c['program_Ir'] + c['system_Ir'] + c['unknown_Ir'] > 0
			assert re.fullmatch('[0-9a-f]{64}', c['profile_sha256'])
	provenance = json.loads((ARCHIVE / 'provenance.json').read_text())
	assert provenance['rnx'] == '002584a48d1f714e3856f5a3d6a99ac86c2204eb'
	assert provenance['rune'] == 'fed878b5aea151a878462d71626c9a4d589a4273'
	assert provenance['acceptance'] == 'PASS'
	assert len(provenance['receipts']) == 8 and all(r['status'] == 'PASS' for r in provenance['receipts'])
	timing = json.loads((ARCHIVE / 'timing.json').read_text())
	assert {(s['layout'], s['role']) for s in timing['samples']} == set(itertools.product(('flat', 'alternating'), ('baseline', 'candidate')))
	assert len(timing['samples']) == 4 and all(s['single_sample'] and s['user_cycles'] > 0 for s in timing['samples'])
	return matrix, timing


def table(matrix, rows, layouts):
	index = {(r['kind'], r['rows'], r['layout'], r['role']): r for r in matrix}
	lines = ['| Kernel / layout | 0205 first | 0206 first | 0205 warm | 0206 warm |', '|---|---:|---:|---:|---:|']
	for kind in KINDS:
		for layout in layouts:
			a, b = [index[kind, rows, layout, role] for role in ('baseline', 'candidate')]
			v = [r['calls'][i]['Ir'] / rows for i in (0, 1) for r in (a, b)]
			lines.append('| ' + LABELS[kind] + ' / ' + layout + ' | ' + ' | '.join(f'{x:.3f}' for x in v) + ' |')
	return '\n'.join(lines)


def render(matrix, timing):
	overview = '''Published **rnx 0206 `002584a` / Rune `fed878b5`** improves nullable
column kernels, adds typed two-input F64 arithmetic and checked constant
multiplication, and counts output validity in words. The explicit
`polars::column_kernel(...).map(...)` API is unchanged.

The table below reports **instructions per row at 100 million rows**, including
Arrow adaptation, output allocation and worker join. Input construction,
preparation and validation are outside the map interval. First and warm calls
are separate; these are individual calls, not repeated-sample means.

'''+table(matrix, 100_000_000, ('flat',))+'''

[Full nullable-layout matrix, timing caveats and evidence hashes](results/column-0206-2026-11-05.md).
The historical 0205 host/Polars comparison below has not been remeasured.
'''
	detail = '''# Column kernels, rnx 0206 — 2026-11-05

Published rnx `002584a48d1f714e3856f5a3d6a99ac86c2204eb` pins Rune
`fed878b5aea151a878462d71626c9a4d589a4273`; baseline is rnx 0205 `bc0fada`.

## Map instructions

Whole-map instructions per row, first/warm calls. Includes Arrow adaptation,
output allocation and worker join; excludes preparation/input construction and
validation. Both sizes use the same paired production binaries. Null layouts
exercise validity handling; no row-by-row interpreter claim applies to the
column path. Large fixtures explicitly use a 1,000,000,000 work budget.

'''
	for rows in (10_000_000, 100_000_000):
		detail += f'### {rows:,} rows\n\n' + table(matrix, rows, LAYOUTS) + '\n\n'
	detail += '''## Separate quiet whole-CLI observations

One sample per binary/layout at 10M rows after a fixed 120-second cooldown and
readiness check, on the same pinned CPU. These user cycles include startup,
input construction, two map calls, validation and teardown. They are **not
map-only or kernel-only timing**, exclude kernel execution, and are not gates.

| Layout | 0205 user cycles | 0206 user cycles | Change |
|---|---:|---:|---:|
'''
	for layout in ('alternating', 'flat'):
		a, b = [next(s for s in timing['samples'] if s['layout'] == layout and s['role'] == role)['user_cycles'] for role in ('baseline', 'candidate')]
		detail += f'| {layout} | {a:,} | {b:,} | {(b/a-1)*100:+.2f}% |\n'
	detail += '''
Flat i64add's +3.4% is an unconfirmed single-sample timing variation, with
protected-map instruction zero growth; it establishes neither a regression nor
its absence. The alternating-null reduction is also a single observation,
not a statistical speedup claim. Baseline wall times were not persisted before
two reporting errors; raw cycle/output samples were recovered without rerunning
successful cases. No wall-time ratio is presented.

## Acceptance and limitations

Fresh acceptance passed all 34 stages; final tooling passed 36 controls. Final
source differs from fresh-accepted and measured production source only in tools
and implementation documentation. The original failed receipts are retained.

Changed column algorithms retain raw instruction ceilings and improvement
checks. Unchanged flat algorithms retain program/unknown zero-growth checks;
libc/loader uses the separately approved bounded accounting. Old interpreted
paths use three-repeat observed envelopes, not confidence intervals, with
candidate-pinned cold compilation constants. A separate, exact memcmp page-guard
exception explains eight extra instructions per fallback with identical caller
counts; allocator residuals remain checked. This is not a blanket zero-overhead
claim or a general exemption for library calls. The field-key comparison cost
is backlogged for a general interned/hashed-key design.

## Archived summaries

[Manifest](column-0206-2026-11-05/MANIFEST.json) pins the compact
[matrix](column-0206-2026-11-05/matrix.json),
[timing samples](column-0206-2026-11-05/timing.json), and
[provenance](column-0206-2026-11-05/provenance.json).
They retain fixture, raw profile, binary and receipt SHA-256 values without
machine names or home-directory paths. Raw machine-specific artifacts remain in
the measurement archive; these public summaries cannot replace raw profiles for
independent re-analysis. No new Polars or other-runtime comparison was run.

Re-render or verify without benchmarks:
`python3 -B scripts/render_column_0206.py [--check]`.
'''
	return overview, detail


def main():
	p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); args = p.parse_args()
	overview, detail = render(*load())
	readme = ROOT / 'README.md'; text = readme.read_text()
	block = '<!-- column-0206:start -->\n\n' + overview + '\n<!-- column-0206:end -->'
	if '<!-- column-0206:start -->' in text:
		text = re.sub(r'<!-- column-0206:start -->.*?<!-- column-0206:end -->', lambda _: block, text, flags=re.S)
	else:
		text = text.replace('## Column kernels — 2026-11-04', '## Column kernels — 2026-11-05\n\n'+block+'\n\n## Historical column comparison — 2026-11-04')
	assert '/home/' not in detail + overview
	if args.check:
		assert readme.read_text() == text and REPORT.read_text() == detail
	else:
		readme.write_text(text); REPORT.write_text(detail)


if __name__ == '__main__':
	main()
