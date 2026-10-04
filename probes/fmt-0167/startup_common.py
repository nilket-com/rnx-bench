"""Shared helpers for the 0068 gate 4 costs-and-regression probe."""
from pathlib import Path
import os, sys, json, time, subprocess, shutil, hashlib, importlib.util
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
B = P.parents[1]
R = B.parent / 'rnx'
T = P / 'target'
O = Path(os.environ.get('RNX_STARTUP_OUT', B / 'results/fmt-0167/startup'))
BASELINE = 'ffa2d4e' # binary built at 89c9ce5; code-identical to closed impl
# # retained stock baseline
PRODUCT = 'a787006' # implementation before evidence
ENV = {k: v for k, v in os.environ.items() if not k.startswith(('GIT_', 'RNX_', 'CARGO_', 'RUST', 'POLARS_'))}
ENV.update(PYTHONDONTWRITEBYTECODE='1', POLARS_MAX_THREADS='1', TERM='xterm-256color', RNX_CONFIG=str(T / 'no-config'),
           RNX_HISTORY=str(T / 'history'), RNX_PROJECT_CACHE=str(T / 'cache'))


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
    return p


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def artifact_of(project):
    receipt = json.loads((project / '.rnx/receipt.json').read_text())
    found = [p for p in (T / 'cache').glob('entries/*/artifacts/*') if p.stat().st_ino == receipt['stamp']['inode']]
    assert len(found) == 1, found
    return found[0]
