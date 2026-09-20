from common import *
for name in ['prepare', 'matrix', 'contract', 'checks']:
    assert (O / f'{name}.json').exists(), name
left = run(['pgrep', '-fa', str(T)], check=False).stdout.decode()
assert not left, left
m = json.loads((O / 'matrix.json').read_text())
save('summary.json', {'product': PRODUCT, 'build_seconds': {k: v['build_seconds'] for k, v in m['cases'].items()}, 'entries': {k: v['compiling_entries'] for k, v in m['cases'].items()},
                      'seed': m['seed'], 'sizes': m['sizes']})
print('all result documents present; no fixture processes remain', flush=True)
