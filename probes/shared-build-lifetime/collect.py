from common import *
for name in ['prepare', 'lifetime', 'catalogue', 'checks']:
    assert (O / f'{name}.json').exists(), name
left = run(['pgrep', '-fa', str(T)], check=False).stdout.decode()
assert not left, left
assert not run(['pgrep', '-f', 'postgres -D .*rnx-pg-contract'], check=False).stdout and not list(Path('/tmp').glob('rnx-pg-contract-*'))
save('summary.json', {'product': PRODUCT, 'documents': sorted(p.name for p in O.iterdir())})
print('all result documents present; no fixture processes remain', flush=True)
