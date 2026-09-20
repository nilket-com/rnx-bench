"""All documents present, every regression check green except the compared root clippy, no fixture processes."""
from common import *
import statistics as st
for name in ['source', 'binaries', 'projects', 'data', 'stock-summary', 'stock-gate', 'polars-summary', 'walkthrough', 'regression', 'clippy-comparison', 'feature-checks']:
    assert (O / f'{name}.json').exists(), name
reg = {r['name']: r['status'] for r in json.loads((O / 'regression.json').read_text())}
assert all(status == 0 for name, status in reg.items() if name not in ('root-clippy', 'baseline-clippy')), reg
assert json.loads((O / 'stock-gate.json').read_text())['passed']
assert not json.loads((O / 'clippy-comparison.json').read_text())['added']
left = run(['pgrep', '-fa', str(T)], ok=False).stdout.decode()
assert not left, left
run(['git', 'worktree', 'remove', '--force', T / 'before'])
stock = json.loads((O / 'stock-summary.json').read_text())
polars = json.loads((O / 'polars-summary.json').read_text())
save('summary.json', {'product': PRODUCT, 'baseline': BASELINE, 'regression': reg,
                      'stock_percent': {m: [round(x['percent'], 2) for x in stock if x['mode'] == m] for m in dict.fromkeys(x['mode'] for x in stock)},
                      'polars_derived_ms': {k: [round(x, 3) for x in v] for k, v in polars['derived'].items()},
                      'prompt_median_ms': {k: [round(x['median_ms'], 2) for x in v] for k, v in polars['prompt'].items()}})
print('gate 4 documents complete; regression green; startup gate passed; worktree removed', flush=True)
