"""Formatting, strict clippy (compared with the baseline's diagnostics), and the suites in the candidate tree."""
from common import *
cand = T / 'candidate'
base = T / 'baseline'
logs = O / 'checks'
logs.mkdir(parents=True, exist_ok=True)
results = {}


def record(name, argv, cwd, timeout=1800, check=True):
    p = run(argv, cwd=cwd, timeout=timeout, check=False)
    (logs / f'{name}.log').write_bytes(p.stdout + p.stderr)
    if check and p.returncode != 0:
        raise SystemExit(f'{name} failed; see {logs / (name + ".log")}')
    return p


def diagnostics(root):
    p = run(['cargo', 'clippy', '--locked', '--offline', '--all-targets', '--', '-D', 'warnings'], cwd=root, timeout=1800, check=False)
    lines = sorted(l for l in (p.stdout + p.stderr).decode(errors='replace').splitlines() if l.startswith(('warning', 'error')) and 'could not compile' not in l)
    return lines


record('root-fmt', ['cargo', 'fmt', '--all', '--check'], cand, timeout=300)
record('polars-fmt', ['cargo', 'fmt', '--check'], cand / 'adapters/polars', timeout=300)
record('tool-fmt', ['cargo', 'fmt', '--check'], cand / 'tools/project', timeout=300)
base_diag = diagnostics(base)
cand_diag = diagnostics(cand)
(logs / 'root-clippy-baseline.log').write_text('\n'.join(base_diag) + '\n')
(logs / 'root-clippy-candidate.log').write_text('\n'.join(cand_diag) + '\n')
assert base_diag == cand_diag, ('root strict clippy diagnostics changed', sorted(set(base_diag) ^ set(cand_diag)))
results['root_clippy'] = {'baseline_diagnostics': len(base_diag), 'candidate_diagnostics': len(cand_diag), 'identical': True}
record('tool-clippy', ['cargo', 'clippy', '--locked', '--offline', '--all-targets', '--features', 'test-support', '--', '-D', 'warnings'], cand / 'tools/project')
record('polars-clippy', ['cargo', 'clippy', '--locked', '--offline', '--all-targets', '--features', 'test-support', '--', '-D', 'warnings'], cand / 'adapters/polars')


def suite(name, argv, cwd):
    p = record(name, argv, cwd, timeout=3600)
    text = p.stdout.decode(errors='replace')
    passed = sum(int(m.group(1)) for m in re.finditer(r'^test result: ok\. (\d+) passed', text, re.M))
    failed = sum(int(m.group(1)) for m in re.finditer(r'(\d+) failed', text) if 'test result' in text)
    assert 'test result: FAILED' not in text, name
    results[name] = {'passed': passed}


import re
suite('root-default', ['cargo', 'test', '--locked', '--offline', '--', '--test-threads=1'], cand)
suite('root-test-support', ['cargo', 'test', '--locked', '--offline', '--features', 'test-support', '--', '--test-threads=1'], cand)
suite('polars-tests', ['cargo', 'test', '--locked', '--offline'], cand / 'adapters/polars')
suite('tool-default', ['cargo', 'test', '--locked', '--offline'], cand / 'tools/project')
suite('tool-test-support', ['cargo', 'test', '--locked', '--offline', '--features', 'test-support'], cand / 'tools/project')
save('checks.json', results)
print('formatting, clippy baseline comparison and all suites pass', flush=True)
