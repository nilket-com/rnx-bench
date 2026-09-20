"""Shared helpers for the shared-compilation probe (rnx at PRODUCT)."""
from pathlib import Path
import os, sys, json, time, subprocess, shutil, hashlib, re, secrets, tomllib
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
B = P.parents[1]
R = B.parent / 'rnx'
T = P / 'target'
O = B / 'results/shared-build-0069'
PRODUCT = 'c6d8a1c'
SHARED = T / 'builds' / 'shared'          # the one canonical shared build directory
SNAPSHOTS = T / 'snapshots'
ENV = {k: v for k, v in os.environ.items() if not k.startswith(('GIT_', 'RNX_', 'CARGO_', 'RUST', 'POLARS_'))}
ENV.update(PYTHONDONTWRITEBYTECODE='1', POLARS_MAX_THREADS='1', TERM='xterm-256color', RNX_CONFIG=str(T / 'no-config'),
           RNX_HISTORY=str(T / 'history'), RNX_PROJECT_CACHE=str(T / 'cache'))


def save(name, x):
    O.mkdir(parents=True, exist_ok=True)
    (O / name).write_text(json.dumps(x, indent=2, ensure_ascii=False) + '\n')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(args, cwd=R, env=ENV, ok=True, timeout=3600, input=None):
    start = time.monotonic()
    p = subprocess.run(list(map(str, args)), cwd=cwd, env=env, capture_output=True, timeout=timeout, input=input)
    seconds = round(time.monotonic() - start, 3)
    O.mkdir(parents=True, exist_ok=True)
    with (O / 'commands.jsonl').open('a') as f:
        f.write(json.dumps({'args': list(map(str, args)), 'cwd': str(cwd), 'status': p.returncode, 'seconds': seconds}) + '\n')
    if ok and p.returncode:
        raise RuntimeError((args, p.stderr.decode(errors='replace')[-8000:]))
    p.seconds = seconds
    return p


def lock_packages(path):
    """Every package record of a Cargo.lock as (name, version, source); path packages have no source."""
    doc = tomllib.loads(Path(path).read_text())
    return {(p['name'], p['version'], p.get('source', 'path')) for p in doc.get('package', [])}


def overlap(runtime, assembly):
    """Name overlap, exact package matches and the differing identities, both ways."""
    r_names = {p[0] for p in runtime}
    a_names = {p[0] for p in assembly}
    shared = r_names & a_names
    exact = {p for p in assembly if p in runtime}
    runtime_only = sorted(p for p in runtime if p[0] in shared and p not in assembly)
    assembly_only = sorted(p for p in assembly if p[0] in shared and p not in runtime)
    return {'runtime_records': len(runtime), 'assembly_records': len(assembly), 'shared_names': len(shared),
            'exact_package_matches': len(exact), 'names_with_exact_match': len({p[0] for p in exact}),
            'runtime_identities_missing_from_assembly': [f'{n} {v}' for n, v, _ in runtime_only],
            'assembly_identities_missing_from_runtime': [f'{n} {v}' for n, v, _ in assembly_only]}


def compiling(stderr):
    """Cargo's `Compiling name vX` log entries, in order (log entries, not rustc invocations)."""
    return re.findall(r'^\s*Compiling ([^ ]+) v(\S+)', stderr, re.M)


def bytes_under(path):
    return sum(f.stat().st_size for f in Path(path).rglob('*') if f.is_file()) if Path(path).exists() else 0


def snapshot(name):
    """Copy the canonical shared directory aside under `name`."""
    dst = SNAPSHOTS / name
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    run(['cp', '-a', SHARED, dst], cwd=T)
    return dst


def restore(name):
    """Put a snapshot back at the canonical path: the same absolute location every build sees."""
    if SHARED.exists():
        shutil.rmtree(SHARED)
    run(['cp', '-a', SNAPSHOTS / name, SHARED], cwd=T)


def discriminate(assembly_dir):
    """A nonrecursive wrapper discriminator: the package name carries a digest of the wrapper's
    body and dependency table, computed before the name exists, so the assembly key that later
    hashes the wrapper is not an input to it."""
    manifest = (assembly_dir / 'Cargo.toml').read_text()
    main = (assembly_dir / 'src/main.rs').read_text()
    deps = manifest.split('[dependencies', 1)[1] if '[dependencies' in manifest else ''
    digest = hashlib.sha256((deps + '\n' + main).encode()).hexdigest()[:16]
    name = f'rnx-app-{digest}'
    manifest = re.sub(r'name = "rnx-project-app"', f'name = "{name}"', manifest, count=1)
    assert name in manifest
    return name, manifest


class Worker:
    """A generated application as a notebook worker, to verify what an executable does."""
    def __init__(self, exe, cwd):
        cr, pw = os.pipe(); pr, cw = os.pipe()
        self.p = subprocess.Popen([str(exe), 'worker', '--control-read', str(cr), '--control-write', str(cw)], pass_fds=[cr, cw],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV, cwd=cwd)
        os.close(cr); os.close(cw)
        self.send = os.fdopen(pw, 'wb', buffering=0)
        self.control = os.fdopen(pr, 'rb', buffering=0)
        self.n = 0
        assert self.reply()['type'] == 'ready'

    def reply(self):
        line = self.control.readline(4 * 1024 * 1024)
        assert line, self.p.stderr.read()[-2000:]
        return json.loads(line)

    def op(self, kind, source=None):
        self.n += 1
        msg = {'op': kind, 'id': self.n, 'nonce': secrets.token_hex(32)}
        if source is not None:
            msg['source'] = source
        self.send.write(json.dumps(msg).encode() + b'\n')
        while True:
            r = self.reply()
            if r['type'] == 'settled':
                self.send.write(json.dumps({'op': 'ack', 'id': self.n}).encode() + b'\n')
                return r

    def close(self):
        self.op('shutdown')
        assert self.p.wait(timeout=10) == 0


def behaviour(exe, cwd):
    """What a bare frame shows, and which natives answer: the executable's observable identity."""
    (Path(cwd) / 'sales.csv').write_text('item,qty\napple,3\n')
    w = Worker(exe, cwd)
    try:
        r = w.op('execute', 'let f = polars::read_csv("sales.csv", [("item","string"),("qty","i64")])?;')
        assert r['failure'] is None, r
        bare = w.op('execute', 'f')['text_plain']
        postgres = w.op('execute', 'postgres::query')['failure'] is None
        retained = w.op('execute', 'probe::retained()')
    finally:
        w.close()
    return {'bare_frame': 'presents' if bare.startswith('DataFrame: ') else 'opaque' if bare == '<::polars::DataFrame>' else bare[:60],
            'postgres': postgres, 'retained': (retained['text_plain'] or '')[:120] if retained['failure'] is None else None}
