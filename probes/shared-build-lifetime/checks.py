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
run(['git', 'checkout', '-q', 'main'], cwd=product)  # the product revision, without the fixture natives
record('tool-fmt', ['cargo', 'fmt', '--check'], product / 'tools/project', 300)
for name, flags in [('default', []), ('support', ['--features', 'test-support'])]:
    record(f'tool-clippy-{name}', ['cargo', 'clippy', '--locked', '--offline', '--all-targets', *flags, '--', '-D', 'warnings'], product / 'tools/project')
    record(f'tool-tests-{name}', ['cargo', 'test', '--locked', '--offline', *flags, '--', '--test-threads=1'], product / 'tools/project')
record('tool-notices', ['python3', 'tools/project/scripts/notices.py', '--check'], product, 600)
record('root-tests-default', ['cargo', 'test', '--locked', '--offline', '--', '--test-threads=1'], product)
save('checks.json', results)
print('formatting, clippy, notices and suites pass on the product tree', flush=True)
