"""The updated walkthrough (examples/polars/SESSION.md), every code block line by line at
the prompt of the presenting application: no diagnostics except the one section 5 provokes
on purpose, bare frames print tables, and the final expressions answer as documented."""
from common import *
import re
term = load('term', B / 'probes/project-interactive/common.py')
projects = json.loads((O / 'projects.json').read_text())
text = (B / 'examples/polars/SESSION.md').read_text()
blocks = re.findall(r'```rune\n(.*?)```', text, re.S)
lines = [l for b in blocks for l in b.splitlines() if l.strip()]
cwd = T / 'walkthrough'
cwd.mkdir()
t = term.Terminal([projects['present']['artifact'], '--no-splash', '--color=never', 'repl'], cwd, ENV)
t.read()
steps = []
for line in lines:
    out = t.send(line)
    body = [x for x in out.splitlines() if x.strip() and not re.match(r'\[\d+\] > ', x) and x.strip() != line.strip()]
    steps.append({'input': line, 'output': '\n'.join(body)})
    if line.startswith(':reset'):
        assert body == ['session reset'], body
    else:
        assert not any(x.startswith(('error', 'runtime error')) for x in body), (line, body)
by_input = {s['input']: s['output'] for s in steps}
assert by_input['sales'].startswith('[') and 'DataFrame: 5 rows × 4 columns' in by_input['sales'] and '"north" | "apple" | 4 | 1.5' in by_input['sales']
assert 'DataFrame: 3 rows × 4 columns' in by_input['big']
assert 'DataFrame: 3 rows × 2 columns' in by_input['by_region'] and '"units": i64' in by_input['by_region']
assert '"qty_plus_10": i64' in by_input['bumped']
assert by_input['oops.is_err()'].endswith('true')
assert 'missing' in by_input['match oops { Ok(_) => "unexpected", Err(e) => e }']
assert by_input['back.preview()? == by_region.preview()?'].endswith('true')
assert 'DataFrame: 5 rows × 4 columns' in by_input['println!("{sales}")'] and not re.match(r'\[\d+\] ', by_input['println!("{sales}")'])
assert by_input['format!("{sales}").len()'].split()[-1].isdigit()
vars_ = by_input[':vars'].splitlines()
# Frames are listed by type, not previewed; the `text` string binding shows the preview quoted.
assert 'sales: DataFrame = <::polars::DataFrame>' in vars_ and all(': DataFrame = <::polars::DataFrame>' in l for l in vars_ if ': DataFrame' in l), vars_
assert any(l.startswith('text: String = "DataFrame: 5 rows') for l in vars_), vars_
assert by_input['polars::lit(1)?'].endswith('<::polars::Expr>')
os.write(t.master, b':quit\n')
t.read(False)
assert t.p.wait(timeout=10) == 0
t.close()
save('walkthrough.json', {'lines': len(lines), 'steps': steps})
print(f'walkthrough: {len(lines)} lines from SESSION.md run at the prompt as documented', flush=True)
