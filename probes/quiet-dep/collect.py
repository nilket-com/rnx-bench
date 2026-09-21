from common import *
for name in ['prepare', 'journey', 'verbose', 'exec_failure', 'compatibility', 'checks']:
    assert (O / f'{name}.json').exists(), name
left = run(['pgrep', '-fa', str(T)], check=False).stdout.decode()
assert not left, left
save('summary.json', {'product': PRODUCT, 'documents': sorted(p.name for p in O.iterdir())})
print('all result documents present; no fixture processes remain', flush=True)
