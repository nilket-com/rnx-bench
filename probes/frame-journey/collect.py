"""All result documents present; no fixture processes remain."""
from common import *
for name in ('prepare', 'journey', 'notebook'):
    assert (O / f'{name}.json').exists(), name
assert (O / 'journey.ipynb').exists()
left = run(['pgrep', '-fa', str(T)], check=False).stdout.decode()
assert not left, left
save('summary.json', {'product_rev': PRODUCT_REV, 'documents': sorted(p.name for p in O.iterdir())})
print('all result documents present; no fixture processes remain', flush=True)
