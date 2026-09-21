"""Shared helpers for the 0070 probe: quiet and verbose dependency preparation at a real prompt."""
import hashlib, json, os, re, select, subprocess, sys, time, importlib.util
from pathlib import Path

sys.dont_write_bytecode = True
H = Path(__file__).resolve().parent
B = H.parents[1]
R = B.parent / 'rnx'
O = B / 'results/quiet-dep-0070'
T = H / 'target'
PRODUCT = '8d33b85'     # the record's impl commit (interim revisions were squashed into it; product source unchanged)
BASELINE = '39beeaa'   # 0069's product: capability version 1, no :depv
ENV = {k: v for k, v in os.environ.items() if not k.startswith(('CARGO_', 'RUST', 'RNX_', 'POLARS_', 'GIT_', 'XDG_'))}
ENV.update(POLARS_MAX_THREADS='1', TERM='xterm-256color', PYTHONDONTWRITEBYTECODE='1')
spec = importlib.util.spec_from_file_location('terminal_fixture', B / 'probes/project-interactive/common.py')
terminal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terminal)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def save(name, value):
    O.mkdir(parents=True, exist_ok=True)
    (O / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def run(argv, cwd=None, timeout=3600, check=True, env=None, input=None):
    start = time.monotonic()
    p = subprocess.run([str(a) for a in argv], cwd=cwd, env=env or ENV, capture_output=True, timeout=timeout, input=input)
    p.seconds = round(time.monotonic() - start, 3)
    O.mkdir(parents=True, exist_ok=True)
    with (O / 'commands.jsonl').open('a') as f:
        f.write(json.dumps({'args': [str(a) for a in argv], 'cwd': str(cwd), 'status': p.returncode, 'seconds': p.seconds}) + '\n')
    if check and p.returncode != 0:
        raise SystemExit(f'{argv[0]} failed ({p.returncode}):\n{p.stdout.decode(errors="replace")[-3000:]}\n{p.stderr.decode(errors="replace")[-3000:]}')
    return p


def git(root, *args):
    return run(['git', '--no-pager', '-c', 'color.ui=false', '-C', root, '-c', 'user.name=probe', '-c', 'user.email=probe@localhost',
                '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', *args])


def home(name, cargo_git=True):
    """A private HOME with state/cache/data dirs, a Cargo home with the registry cache, and no Git checkouts unless kept."""
    d = T / 'homes' / name
    (d / 'cargo').mkdir(parents=True, exist_ok=True)
    if not (d / 'cargo/registry').exists():
        (d / 'cargo/registry').symlink_to(Path.home() / '.cargo/registry', target_is_directory=True)
    # A private HOME loses rustup's default toolchain: name the real rustup home, which the tool admits.
    env = dict(ENV, HOME=str(d), CARGO_HOME=str(d / 'cargo'), RUSTUP_HOME=str(Path.home() / '.rustup'), XDG_STATE_HOME=str(d / 'state'),
               XDG_DATA_HOME=str(d / 'data'), XDG_CACHE_HOME=str(d / 'cache'), RNX_CONFIG=str(d / 'no-config'), RNX_HISTORY=str(d / 'history'))
    return d, env


def until(t, needle, timeout=60):
    out = ''
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if select.select([t.master], [], [], .1)[0]:
            b = os.read(t.master, 65536)
            t.log += b
            out += terminal.text(b)
            if needle in out:
                return out
    raise AssertionError((needle, out[-2000:]))


def body(out):
    return [x for x in out.replace('\r', '').split('\n') if x.strip() and not re.match(r'\[\d+\] > ', x)]


def session(exe, env, cwd, extra=None, splash=False):
    cwd.mkdir(parents=True, exist_ok=True)
    e = dict(env)
    if extra:
        e.update(extra)
    t = terminal.Terminal([exe, *([] if splash else ['--no-splash']), '--color=never'], cwd, e)
    t.read()
    return t


def quit(t):
    os.write(t.master, b':q\n')
    t.read(False)
    assert t.p.wait(timeout=10) == 0
    t.close()
