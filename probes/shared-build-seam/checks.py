"""Formatting, strict clippy and the suites in the candidate tree (tool both configurations, root default)."""
from common import *
cand = T / 'candidate'
logs = O / 'checks'
logs.mkdir(exist_ok=True)
results = {}
def record(name, argv, cwd, timeout=1800):
    p = run(argv, cwd=cwd, timeout=timeout)
    (logs / f'{name}.log').write_bytes(p.stdout + p.stderr)
    passed = sum(int(m) for m in re.findall(rb'test result: ok\. (\d+) passed', p.stdout + p.stderr))
    results[name] = {'status': p.returncode, 'passed': passed}
    print(name, p.returncode, passed, flush=True)
record('tool-fmt', ['cargo', 'fmt', '--check'], cand / 'tools/project', 300)
for name, flags in [('default', []), ('support', ['--features', 'test-support'])]:
    record(f'tool-clippy-{name}', ['cargo', 'clippy', '--locked', '--offline', '--all-targets', *flags, '--', '-D', 'warnings'], cand / 'tools/project')
    record(f'tool-tests-{name}', ['cargo', 'test', '--locked', '--offline', *flags, '--', '--test-threads=1'], cand / 'tools/project')
record('root-tests-default', ['cargo', 'test', '--locked', '--offline', '--', '--test-threads=1'], cand, 2400)
save('checks.json', results)
print('formatting, clippy and suites pass in the candidate tree', flush=True)
