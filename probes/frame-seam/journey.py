"""A real generated Polars application with `presentation = true`: bare frames show the bounded preview."""
from common import *
import re, sys, time
sys.path.insert(0, str(B / 'probes/project-interactive'))
import importlib.util
spec = importlib.util.spec_from_file_location('terminal_fixture', B / 'probes/project-interactive/common.py')
terminal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terminal)
runtime = T / 'candidate'
work = T / 'journey'
work.mkdir(exist_ok=True)
cache = work / 'cache'
project = work / 'project'
project.mkdir(exist_ok=True)
(project / 'main.rn').write_text('pub fn main(_) { 42 }\n')
(project / 'rnx.toml').write_text(
    f'format = 1\n[application]\nentry = "main.rn"\n[runtime]\npath = "{runtime}"\n'
    f'[native.polars]\npath = "{runtime}/adapters/polars"\npackage = "rnx-polars"\nbuilder = "build"\nhook = "plain"\npresentation = true\n')
env = dict(ENV, RNX_PROJECT_CACHE=str(cache), RNX_HISTORY=str(work / 'history'), RNX_CONFIG=str(work / 'absent-config'))
t0 = time.time()
run([tool('candidate'), 'lock', '--manifest', project / 'rnx.toml', '--offline'], env=env, timeout=600)
build = run([tool('candidate'), 'build', '--manifest', project / 'rnx.toml', '--offline'], env=env, timeout=1800)
build_seconds = time.time() - t0
wrapper = json.loads(json.loads((project / 'rnx.lock').read_text())['assembly']['identity'])['main']
assert '.present("polars", native_0::present)' in wrapper
cwd = work / 'cwd'
cwd.mkdir(exist_ok=True)
for f in ('sales.csv', 'wide.csv'):
    try:
        (cwd / f).unlink()
    except FileNotFoundError:
        pass
env['TERM'] = 'xterm-256color'
t = terminal.Terminal([tool('candidate'), 'session', '--manifest', project / 'rnx.toml', '--no-splash'], cwd=cwd, env=env)
t.read()


def body(out):
    return '\n'.join(x for x in out.splitlines() if x.strip() and not re.match(r'\[\d+\] > ', x))


steps = {}
def step(name, line, expect=None, absent=None):
    out = body(t.send(line))
    steps[name] = {'input': line, 'output': out}
    for s in (expect or []):
        assert s in out, (name, s, out)
    for s in (absent or []):
        assert s not in out, (name, s, out)


step('csv', 'fs::write_new("sales.csv", "region,item,qty,price\\nwest,apple,3,1.5\\nwest,pear,1,2.0\\neast,apple,5,1.5\\neast,plum,2,3.0\\nnorth,apple,4,1.5\\n")?;')
step('read', 'let sales = polars::read_csv("sales.csv", [("region","string"),("item","string"),("qty","i64"),("price","f64")])?;')
step('bare', 'sales', expect=['[3] DataFrame: 5 rows × 4 columns', '"region": string | "item": string | "qty": i64 | "price": f64', '"north" | "apple" | 4 | 1.5'], absent=['<::polars::DataFrame>'])
step('explicit', 'format!("{sales}")', expect=['DataFrame: 5 rows × 4 columns'])
step('println', 'println!("{sales}")', expect=['"west" | "apple" | 3 | 1.5'])
step('suppressed', 'let again = sales;', absent=['DataFrame'])
step('container', '[sales]', expect=['[<::polars::DataFrame>]'], absent=['rows ×'])
step('result', 'sales.lazy().collect()', expect=['Ok(<::polars::DataFrame>)'], absent=['rows ×'])
step('lazy', 'sales.lazy()', expect=['<::polars::LazyFrame>'], absent=['rows ×'])
step('expr', 'polars::col("qty")', expect=['<::polars::Expr>'])
step('preview-string', 'sales.preview()?', expect=['"DataFrame: 5 rows'])
step('filtered', 'sales.lazy().filter(polars::col("qty").gt(polars::lit(2)?)).collect()?', expect=['DataFrame: 3 rows × 4 columns'])
step('error', 'sales.lazy().filter(polars::col("missing").gt(polars::lit(1)?)).collect().is_err()', expect=['true'])
step('still-there', 'sales', expect=['DataFrame: 5 rows × 4 columns'])
# A frame wider than 8 columns and taller than 10 rows shows the omission line.
header = ','.join(f'c{i}' for i in range(12))
rows = '\\n'.join(','.join(str(r * 100 + c) for c in range(12)) for r in range(15))
step('wide-csv', f'fs::write_new("wide.csv", "{header}\\n{rows}\\n")?;')
step('wide-read', 'let wide = polars::read_csv("wide.csv", [' + ','.join(f'("c{i}","i64")' for i in range(12)) + '])?;')
step('wide', 'wide', expect=['DataFrame: 15 rows × 12 columns', '[5 rows and 4 columns omitted by display limits]'])
step('reset', ':reset')
step('after-reset', 'polars::read_csv("sales.csv", [("region","string"),("item","string"),("qty","i64"),("price","f64")])?', expect=['DataFrame: 5 rows × 4 columns'])
import os
os.write(t.master, b':q\n')
t.read(False)
assert t.p.wait(timeout=5) == 0
t.close()
save('journey.json', {'build_seconds': round(build_seconds, 1), 'wrapper': wrapper, 'steps': steps})
print('bare frames present through the generated application; containers, lazy plans and strings unchanged', flush=True)
