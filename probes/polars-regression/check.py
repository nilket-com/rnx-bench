"""Replay gate-six checks into a fresh directory, keeping accepted logs intact."""
import argparse
import json
from pathlib import Path
import re
import subprocess

BENCH = Path(__file__).resolve().parents[2]
ROOT = BENCH.parent / 'rnx'
EVIDENCE = BENCH / 'results/polars-regression-0058'
p = argparse.ArgumentParser()
p.add_argument('output', type=Path)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
results = []
for group, cwd in [('root', ROOT), ('adapter', ROOT / 'adapters/polars')]:
    checks = json.loads((EVIDENCE / f'{group}-checks.json').read_text())
    if group == 'root':
        checks += [
            {'name': 'root-clippy', 'command': ['cargo', 'clippy', '--locked', '--all-targets', '--all-features', '--', '-D', 'warnings']},
            {'name': 'root-clippy-baseline-mode', 'command': ['cargo', 'clippy', '--locked', '--all-targets', '--all-features']},
        ]
    else:
        checks += [{'name': 'adapter-notices', 'command': ['python3', 'scripts/third-party-notices.py', '--check']}]
    for c in checks:
        with (a.output / (c['name'] + '.log')).open('w') as f:
            r = subprocess.run(c['command'], cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
        row = dict(c, exit=r.returncode)
        results.append(row)
        (a.output / 'checks.json').write_text(json.dumps(results, indent=2) + '\n')
        print(c['name'], r.returncode, flush=True)
        # These are recorded limitations, not passing checks. A new outcome
        # deserves inspection rather than treating every failure as expected.
        if c['name'] not in {'adapter-windows', 'root-clippy', 'root-clippy-baseline-mode'}:
            assert r.returncode == 0, row

def diagnostics(path):
    return sorted(m.groups() for m in re.finditer(
        r'^(warning|error): (.+)\n\s+--> (.+)', path.read_text(), re.M))
assert diagnostics(a.output / 'root-clippy-baseline-mode.log') == diagnostics(
    BENCH / 'results/project-regression-0057/before-clippy-features.log')
tree = subprocess.check_output(['cargo', 'tree', '--locked', '--prefix', 'none'], cwd=ROOT, text=True)
(a.output / 'root-tree.txt').write_text(tree)
old = (BENCH / 'results/project-regression-0057/default-tree-before.txt').read_text()
assert tree.replace(str(ROOT), 'ROOT') == old.replace('/tmp/rnx-0057-startup-before', 'ROOT')
print('Linux checks and unchanged baseline comparisons pass; inspect Windows and lint logs separately')
