from common import *
for name in ['source', 'binaries', 'origin', 'stock-summary', 'stock-gate', 'transition-summary', 'regression', 'clippy-comparison', 'feature-checks']:
    assert (O / f'{name}.json').exists(), name
reg = {r['name']: r['status'] for r in json.loads((O / 'regression.json').read_text())}
assert all(status == 0 for name, status in reg.items() if name not in ('root-clippy', 'baseline-clippy')), reg
assert json.loads((O / 'stock-gate.json').read_text())['passed']
assert not json.loads((O / 'clippy-comparison.json').read_text())['added']
left = run(['pgrep', '-fa', str(T)], ok=False).stdout.decode()
assert not left, left
if (T / 'before').exists():
    run(['git', 'worktree', 'remove', '--force', T / 'before'])
stock = json.loads((O / 'stock-summary.json').read_text())
tr = json.loads((O / 'transition-summary.json').read_text())
save('summary.json', {'product': PRODUCT, 'baseline': BASELINE, 'regression': reg,
                      'stock_percent': {mode: [round(x['percent'], 2) for x in stock if x['mode'] == mode] for mode in dict.fromkeys(x['mode'] for x in stock)},
                      'transition': tr})
print('gate 3 documents complete; regression green; startup gate passed; worktree removed', flush=True)
