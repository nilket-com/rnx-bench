"""The transition's wall time with and without capture: `:dep polars` against `:depv polars` from a
fresh session each time, interleaved, warm (Polars built once, so each is a
resolve, an attach, a startup check and a restart); and one cold first build each way."""
from common import *
import random, re, statistics as st, select, importlib.util
spec = importlib.util.spec_from_file_location('terminal_fixture', B / 'probes/project-interactive/common.py')
terminal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terminal)
# No core pinning: the affinity would be inherited by Cargo and serialise the cold builds.
rnx = json.loads((O / 'origin.json').read_text())['installed']
journal = O / 'transition-samples.jsonl'
assert not journal.exists()
rows = []


def record(x):
    rows.append(x)
    with journal.open('a') as f:
        f.write(json.dumps(x) + '\n')


def home(name):
    d = T / 'homes' / name
    (d / 'cargo').mkdir(parents=True, exist_ok=True)
    (d / 'work').mkdir(exist_ok=True)
    if not (d / 'cargo/registry').exists():
        (d / 'cargo/registry').symlink_to(Path.home() / '.cargo/registry', target_is_directory=True)
    env = dict(ENV, HOME=str(d), CARGO_HOME=str(d / 'cargo'), RUSTUP_HOME=str(Path.home() / '.rustup'), XDG_STATE_HOME=str(d / 'state'),
               XDG_DATA_HOME=str(d / 'data'), XDG_CACHE_HOME=str(d / 'cache'), RNX_CONFIG=str(d / 'no-config'), RNX_HISTORY=str(d / 'history'),
               RNX_PROJECT_CACHE=str(d / 'project-cache'))  # the probe-wide cache root would let the homes share entries
    return d, env


def until(t, needle, timeout):
    out = ''
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if select.select([t.master], [], [], .05)[0]:
            b = os.read(t.master, 65536)
            t.log += b
            out += terminal.text(b)
            if needle in out:
                return out
    raise AssertionError((needle, out[-1500:]))


def prepare(env, cwd, spelling, name):
    """Send the line at a fresh prompt; time from the line to the replacement's first prompt."""
    t = terminal.Terminal([rnx, '--no-splash', '--color=never'], cwd, env)
    t.read()
    begin = time.perf_counter_ns()
    os.write(t.master, f'{spelling} polars\n'.encode())
    if spelling == ':depv':
        until(t, 'Continue? [y/N]', 120)
        os.write(t.master, b'y\n')
    try:
        out = t.read(timeout=1800)
    finally:
        (O / 'screens').mkdir(exist_ok=True)
        (O / f'screens/{name}.txt').write_bytes(t.log)
    ns = time.perf_counter_ns() - begin
    assert re.search(r'\[1\] > \r*$', out), out[-300:]
    # After the clock: the replacement must have Polars (a refused request also ends at a
    # prompt), and the quiet screen must be the echoed line and the new prompt, nothing else.
    os.write(t.master, b'polars::lit(42).is_ok()\n')
    assert 'true' in t.read(), out[-300:]
    if spelling == ':dep':
        lines = [l for l in re.sub(r'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07\x1b]*|\x1b\[[0-9;]*t', '', out).replace('\r', '').split('\n') if l.strip()]
        assert lines == [':dep polars', '[1] > '] or lines == ['[1] > :dep polars', '[1] > '], lines
    os.write(t.master, b':q\n')
    t.read(False)
    assert t.p.wait(timeout=10) == 0
    t.close()
    return ns


# Cold: one first build each way, in separate homes.
cold = {}
for spelling in [':dep', ':depv']:
    d, env = home('cold-' + spelling.strip(':'))
    ns = prepare(env, d / 'work', spelling, 'cold-' + spelling.strip(':'))
    cold[spelling] = ns / 1e9
    record({'section': 'cold', 'spelling': spelling, 'ns': ns})
    print(f'cold {spelling}: {ns / 1e9:.1f} s', flush=True)
# Warm: one home with Polars built, then interleaved fresh-session preparations.
d, env = home('warm')
prepare(env, d / 'work', ':dep', 'warm-build')
for spelling in [':dep', ':depv']:
    prepare(env, d / 'work', spelling, 'warm-first-' + spelling.strip(':'))
for repeat in range(2):
    jobs = [(s, i) for s in [':dep', ':depv'] for i in range(10)]
    random.Random(700200 + repeat).shuffle(jobs)
    for spelling, i in jobs:
        ns = prepare(env, d / 'work', spelling, 'last')
        record({'section': 'warm', 'repeat': repeat, 'sample': i, 'spelling': spelling, 'ns': ns})
    print(f'warm repeat {repeat} complete', flush=True)
summary = {'cold_s': cold, 'warm': {}}
for spelling in [':dep', ':depv']:
    per = []
    for repeat in range(2):
        v = sorted(x['ns'] / 1e9 for x in rows if x['section'] == 'warm' and x['spelling'] == spelling and x['repeat'] == repeat)
        per.append({'median_s': st.median(v), 'p10_s': v[len(v) // 10], 'p90_s': v[len(v) * 9 // 10]})
    summary['warm'][spelling] = per
summary['warm_delta_s'] = [summary['warm'][':dep'][r]['median_s'] - summary['warm'][':depv'][r]['median_s'] for r in range(2)]
save('transition-summary.json', summary)
save('transition-conditions.json', {'pinned': False, 'samples': len(rows), 'seeds': [700200, 700201], 'clock': 'line written to replacement first prompt, PTY; verbose includes answering the prompt'})
print(json.dumps(summary, indent=1), flush=True)
assert all(abs(x) < 2.0 for x in summary['warm_delta_s']), summary['warm_delta_s']
