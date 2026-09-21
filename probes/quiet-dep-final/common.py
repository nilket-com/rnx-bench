"""Shared helpers for the 0070 gate 3 costs-and-regression probe."""
from pathlib import Path
import os, sys, json, time, subprocess, shutil, hashlib, importlib.util
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
B = P.parents[1]
R = B.parent / 'rnx'
T = P / 'target'
O = B / 'results/quiet-dep-final-0070'
BASELINE = '39beeaa'   # the product before this record (0069's product)
PRODUCT = '8d33b85'     # the record's impl commit (interim revisions were squashed into it; product source unchanged)
ENV = {k: v for k, v in os.environ.items() if not k.startswith(('GIT_', 'RNX_', 'CARGO_', 'RUST', 'POLARS_'))}
import secrets, tomllib
ENV.update(PYTHONDONTWRITEBYTECODE='1', POLARS_MAX_THREADS='1', TERM='xterm-256color', RNX_CONFIG=str(T / 'no-config'),
           RNX_HISTORY=str(T / 'history'), RNX_PROJECT_CACHE=str(T / 'cache'), CARGO_HOME=str(T / 'cargo-home'))


def save(name, x):
    O.mkdir(parents=True, exist_ok=True)
    (O / name).write_text(json.dumps(x, indent=2, ensure_ascii=False) + '\n')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(args, cwd=R, env=ENV, ok=True, timeout=2400, input=None):
    start = time.monotonic()
    p = subprocess.run(list(map(str, args)), cwd=cwd, env=env, capture_output=True, timeout=timeout, input=input)
    O.mkdir(parents=True, exist_ok=True)
    with (O / 'commands.jsonl').open('a') as f:
        f.write(json.dumps({'args': list(map(str, args)), 'cwd': str(cwd), 'status': p.returncode, 'seconds': round(time.monotonic() - start, 3)}) + '\n')
    if ok and p.returncode:
        raise RuntimeError((args, p.stderr.decode(errors='replace')[-8000:]))
    p.seconds = round(time.monotonic() - start, 3)
    return p


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def artifact_of(project, cache):
    receipt = json.loads((project / '.rnx/receipt.json').read_text())
    found = [p for p in Path(cache).glob('entries/*/artifacts/*') if p.stat().st_ino == receipt['stamp']['inode']]
    assert len(found) == 1, found
    return found[0]


def git(root, *args):
    return run(['git', '--no-pager', '-c', 'color.ui=false', '-C', root, '-c', 'user.name=probe', '-c', 'user.email=probe@localhost',
                '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', *args], cwd=root)


def bare_frame(exe, cwd):
    """What a bare frame shows through the worker, and whether PostgreSQL is present."""
    cwd = Path(cwd)
    cwd.mkdir(parents=True, exist_ok=True)
    (cwd / 'sales.csv').write_text('item,qty\napple,3\n')
    cr, pw = os.pipe(); pr, cw = os.pipe()
    p = subprocess.Popen([str(exe), 'worker', '--control-read', str(cr), '--control-write', str(cw)], pass_fds=[cr, cw], stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV, cwd=cwd)
    os.close(cr); os.close(cw)
    send = os.fdopen(pw, 'wb', buffering=0); control = os.fdopen(pr, 'rb', buffering=0)
    n = 0
    def op(kind, source=None):
        nonlocal n
        n += 1
        msg = {'op': kind, 'id': n, 'nonce': secrets.token_hex(32)}
        if source is not None:
            msg['source'] = source
        send.write(json.dumps(msg).encode() + b'\n')
        while True:
            r = json.loads(control.readline(4 * 1024 * 1024))
            if r['type'] == 'settled':
                send.write(json.dumps({'op': 'ack', 'id': n}).encode() + b'\n')
                return r
    assert json.loads(control.readline(4 * 1024 * 1024))['type'] == 'ready'
    op('execute', 'let f = polars::read_csv("sales.csv", [("item","string"),("qty","i64")])?;')
    text = op('execute', 'f')['text_plain']
    postgres = op('execute', 'postgres::query')['failure'] is None
    op('shutdown')
    assert p.wait(timeout=10) == 0
    return {'bare_frame': 'presents' if text.startswith('DataFrame: ') else 'opaque' if text == '<::polars::DataFrame>' else text[:60], 'postgres': postgres}
