"""The interactive journey at a real prompt (pseudo-terminal, xterm-256color, 30x120):
a project built by the tool, sales.csv, bare frames, a filter, a query error, recovery,
omission markers for a wide and tall frame, numbering, suppression, reset, history, quit."""
from common import *
import importlib.util, os, re
spec = importlib.util.spec_from_file_location('terminal_fixture', B / 'probes/project-interactive/common.py')
terminal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terminal)
project = T / 'project'
work = T / 'journey'
work.mkdir(exist_ok=True)
history = work / 'history'
history.unlink(missing_ok=True)
env = dict(ENV, RNX_PROJECT_CACHE=str(T / 'cache'), RNX_HISTORY=str(history), RNX_CONFIG=str(work / 'absent-config'))
cwd = work / 'cwd'
cwd.mkdir(exist_ok=True)
for f in ('sales.csv', 'wide.csv'):
    (cwd / f).unlink(missing_ok=True)
(cwd / 'sales.csv').write_text(SALES)
(cwd / 'wide.csv').write_text(f'{WIDE_HEADER}\n{WIDE_ROWS}\n')
t = terminal.Terminal([RNX, 'project', 'session', '--manifest', project / 'rnx.toml', '--no-splash'], cwd=cwd, env=env)
banner = t.read()
pid = t.p.pid
artifact = os.readlink(f'/proc/{pid}/exe')
assert artifact.startswith(str(T / 'cache')), artifact


def body(out, line=None):
    # Drop prompt lines and the terminal's echo of the submitted line, which
    # arrives on the prompt line or, depending on read timing, on its own.
    lines = [x for x in out.splitlines() if x.strip() and not re.match(r'\[\d+\] > ', x)]
    if line is not None and lines and lines[0].strip() == line.strip():
        lines = lines[1:]
    return '\n'.join(lines)


steps = []
def step(name, line, expect=(), absent=(), number=None):
    out = body(t.send(line), line)
    steps.append({'name': name, 'input': line, 'output': out})
    for s in expect:
        assert s in out, (name, s, out)
    for s in absent:
        assert s not in out, (name, s, out)
    if number is not None:
        assert out.startswith(f'[{number}] '), (name, number, out)
    return out


table = ['DataFrame: 5 rows × 4 columns', '"region": string | "item": string | "qty": i64 | "price": f64', '"west" | "apple" | 3 | 1.5', '"north" | "apple" | 4 | 1.5']
step('read', f'let sales = polars::read_csv("sales.csv", {SALES_SCHEMA})?;', absent=['DataFrame'])
step('bare', 'sales', expect=table, absent=['<::polars::DataFrame>'], number=2)
step('filter', 'let big = sales.lazy().filter(polars::col("qty").gt(polars::lit(2)?)).collect()?;', absent=['DataFrame'])
step('filtered', 'big', expect=['DataFrame: 3 rows × 4 columns', '"east" | "apple" | 5 | 1.5'], absent=['"pear"'], number=4)
# A query error at the prompt: reported, the session continues, bindings survive.
error = step('error', 'sales.lazy().filter(polars::col("missing").gt(polars::lit(1)?)).collect()?', expect=['error'], absent=['DataFrame: '])
step('recover', 'sales', expect=table, number=6)
step('big-again', 'big', expect=['DataFrame: 3 rows × 4 columns'], number=7)
step('wide-read', f'let wide = polars::read_csv("wide.csv", {WIDE_SCHEMA})?;')
step('wide', 'wide', expect=['DataFrame: 15 rows × 12 columns', '[5 rows and 4 columns omitted by display limits]', '"c0": i64 | "c1": i64', '"c7": i64\n', '900 | 901'], absent=['"c8"', '1000 | '], number=9)
step('suppressed', 'let x = sales;', absent=['DataFrame', '['])
step('explicit', 'println!("{sales}")', expect=table, absent=['[11]'])
step('numbered-after-suppression', 'x', expect=table, number=12)
step('vars', ':vars', expect=['sales', 'big', 'wide', 'x'], absent=['DataFrame: '])
reset = step('reset', ':reset', expect=['session reset'])
step('gone', 'sales', expect=['error'], absent=['DataFrame: '])
step('after-reset', f'polars::read_csv("sales.csv", {SALES_SCHEMA})?', expect=table, number=2)
os.write(t.master, b':quit\n')
t.read(False)
assert t.p.wait(timeout=10) == 0
t.close()
(work / 'session.pty').write_bytes(t.log)
saved = history.read_text()
assert 'sales' in saved.splitlines() and 'let x = sales;' in saved, saved
# History survives: the next session recalls the last input with the up arrow.
t = terminal.Terminal([RNX, 'project', 'session', '--manifest', project / 'rnx.toml', '--no-splash'], cwd=cwd, env=env)
t.read()
# Commands are history too: the last entry is `:quit`, the one before it the read.
os.write(t.master, b'\x1b[A')
recalled = t.read(False, timeout=2)
assert recalled.rstrip().endswith(':quit'), recalled
os.write(t.master, b'\x1b[A')
recalled += t.read(False, timeout=2)
assert 'polars::read_csv("sales.csv"' in recalled, recalled
os.write(t.master, b'\n')
out = body(t.read())
assert 'DataFrame: 5 rows × 4 columns' in out and out.startswith('[1] '), out
os.write(t.master, b':quit\n')
t.read(False)
assert t.p.wait(timeout=10) == 0
t.close()
assert not run(['pgrep', '-f', artifact], check=False).stdout
save('journey.json', {'artifact': artifact, 'banner': banner[:400], 'steps': steps,
                      'history': saved, 'recalled': recalled})
print(f'interactive journey: bare frames, filter, error recovery, omission markers, numbering, suppression, reset, history and quit at a real prompt', flush=True)
