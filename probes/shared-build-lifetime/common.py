"""Shared helpers for the 0069 gate 3 lifetime probe (product at PRODUCT)."""
import hashlib, json, os, re, secrets, subprocess, sys, time, tomllib
from pathlib import Path

sys.dont_write_bytecode = True
H = Path(__file__).resolve().parent
B = H.parents[1]
R = B.parent / 'rnx'
O = B / 'results/shared-build-lifetime-0069'
T = H / 'target'
PRODUCT = 'e69d06b'
ENV = {k: v for k, v in os.environ.items() if not k.startswith(('CARGO_', 'RUST', 'RNX_', 'POLARS_', 'GIT_'))}
ENV.update(POLARS_MAX_THREADS='1', TERM='xterm-256color', PYTHONDONTWRITEBYTECODE='1')
RNX = T / 'product/target/release/rnx'
CACHE = T / 'cache'
CARGO_HOME = T / 'cargo-home'


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


def env_for(extra=None):
    e = dict(ENV, RNX_PROJECT_CACHE=str(CACHE), RNX_HISTORY=str(T / 'history'), RNX_CONFIG=str(T / 'absent-config'), CARGO_HOME=str(CARGO_HOME))
    if extra:
        e.update(extra)
    return e


def origin():
    d = json.loads((O / 'prepare.json').read_text())
    return d['origin_url'], d['origin_rev']


def project(name, natives, rev=None, runtime_only=False):
    """A format-2 project on the fixture origin; natives is [(name, package, hook, extra fields)]."""
    url, origin_rev = origin()
    rev = rev or origin_rev
    d = T / 'projects' / name
    d.mkdir(parents=True, exist_ok=True)
    (d / 'main.rn').write_text('pub fn main(_) { 42 }\n')
    text = f'format = 2\n[application]\nentry = "main.rn"\n[runtime]\ngit = "{url}"\nrev = "{rev}"\n'
    for n, package, hook, fields in natives:
        text += f'\n[native.{n}]\ngit = "{url}"\nrev = "{rev}"\npackage = "{package}"\nbuilder = "build"\nhook = "{hook}"\n{fields}'
    (d / 'rnx.toml').write_text(text)
    return d


def lock_and_build(d, env=None):
    env = env or env_for()
    lock = run([RNX, 'project', 'lock', '--manifest', d / 'rnx.toml'], cwd=d, env=env, timeout=900)
    build = run([RNX, 'project', 'build', '--manifest', d / 'rnx.toml'], cwd=d, env=env, timeout=3600, check=False)
    return lock, build


def identity_of(d):
    return json.loads(json.loads((d / 'rnx.lock').read_text())['assembly']['identity'])


def artifact_of(d):
    receipt = json.loads((d / '.rnx/receipt.json').read_text())
    found = [p for p in CACHE.glob('entries/*/artifacts/*') if p.stat().st_ino == receipt['stamp']['inode']]
    assert len(found) == 1, found
    return found[0]


def compiling(stderr):
    return len(re.findall(r'^\s*Compiling ', stderr, re.M))


def behaviour(exe, cwd, pg_url=None, retained_path=None):
    """Through the worker: a bare frame, a real PostgreSQL query when a cluster URL is given, the
    embedding retained-output probe, and the runtime-configuration reader when its path is given."""
    cwd = Path(cwd)
    (cwd / 'sales.csv').write_text('item,qty\napple,3\n')
    cr, pw = os.pipe(); pr, cw = os.pipe()
    env = dict(ENV)
    if retained_path:
        env['PROBE_RETAINED_PATH'] = str(retained_path)
    p = subprocess.Popen([str(exe), 'worker', '--control-read', str(cr), '--control-write', str(cw)], pass_fds=[cr, cw], stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=cwd)
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
    frame = op('execute', 'let f = polars::read_csv("sales.csv", [("item","string"),("qty","i64")])?;')
    bare = op('execute', 'f')['text_plain'] if frame['failure'] is None else None
    postgres = op('execute', 'postgres::query')['failure'] is None
    query = None
    if pg_url and postgres:
        r = op('execute', f'let row = postgres::query({json.dumps(pg_url)}, "SELECT 40 + 2 AS answer, current_database() AS db", [], #{{}}).await?; row')
        query = (r['text_plain'] or '')[:160] if r['failure'] is None else f"failure: {str(r['failure'])[:160]}"
    retained = op('execute', 'probe::retained()')
    configured = op('execute', 'probe_config::retained()')
    op('shutdown')
    assert p.wait(timeout=10) == 0
    return {'bare_frame': None if bare is None else 'presents' if bare.startswith('DataFrame: ') else 'opaque' if bare == '<::polars::DataFrame>' else bare[:60],
            'postgres': postgres, 'query': query, 'retained': (retained['text_plain'] or '')[:120] if retained['failure'] is None else None,
            'configured': (configured['text_plain'] or '')[:400] if configured['failure'] is None else None}


def lock_packages(path):
    doc = tomllib.loads(Path(path).read_text())
    return {(p['name'], p['version'], p.get('source', 'path')) for p in doc.get('package', [])}
