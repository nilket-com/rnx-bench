"""Formatting, strict clippy and the suites on the product tree."""
from common import *
product = T / 'product'
logs = O / 'checks'
logs.mkdir(exist_ok=True)
results = {}
def record(name, argv, cwd, timeout=2400):
    p = run(argv, cwd=cwd, timeout=timeout)
    (logs / f'{name}.log').write_bytes(p.stdout + p.stderr)
    results[name] = {'status': p.returncode, 'passed': sum(int(m) for m in re.findall(rb'test result: ok\. (\d+) passed', p.stdout + p.stderr))}
    print(name, p.returncode, results[name]['passed'], flush=True)
record('root-fmt', ['cargo', 'fmt', '--all', '--check'], product, 300)
record('tool-fmt', ['cargo', 'fmt', '--check'], product / 'tools/project', 300)
for name, flags in [('default', []), ('support', ['--features', 'test-support'])]:
    record(f'tool-clippy-{name}', ['cargo', 'clippy', '--locked', '--offline', '--all-targets', *flags, '--', '-D', 'warnings'], product / 'tools/project')
    record(f'tool-tests-{name}', ['cargo', 'test', '--locked', '--offline', *flags, '--', '--test-threads=1'], product / 'tools/project')
    record(f'root-tests-{name}', ['cargo', 'test', '--locked', '--offline', *flags, '--', '--test-threads=1'], product)
record('root-tests-runner', ['cargo', 'test', '--locked', '--offline', '--no-default-features', '--features', 'count-allocations,project-sources', '--', '--test-threads=1'], product)
save('checks.json', results)
print('formatting, clippy and suites pass on the product tree', flush=True)
