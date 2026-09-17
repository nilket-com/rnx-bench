from pathlib import Path
import hashlib, json, os, subprocess, sys, time

# The shared terminal fixture lives outside this probe's ignored target tree.
sys.dont_write_bytecode = True

H = Path(__file__).resolve().parent
B = H.parents[1]
R = B.parent / 'rnx'
O = B / 'results/adapter-commands-0062/real'
W = H / 'target'
T = R / 'tools/project/target/release/rnx-project'
CACHE = W / 'cache'
APPS = [W / 'first', W / 'second']
ENV = {k: v for k, v in os.environ.items() if not k.startswith(('CARGO_', 'RUST', 'RNX_', 'POLARS_'))}
ENV.update(RNX_PROJECT_CACHE=str(CACHE), POLARS_MAX_THREADS='1', TERM='xterm-256color',
           RNX_CONFIG=str(W / 'absent-config'), RNX_HISTORY=str(W / 'history'))

def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def save(name, value):
    (O / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def command(op, app=APPS[0], tail=()):
    return [str(T), op, '--manifest', str(app / 'rnx.toml'), *map(str, tail)]

def receipt(app):
    return json.loads((app / '.rnx/receipt.json').read_text())

def artifact(app=APPS[0]):
    r = receipt(app)
    return CACHE / 'entries' / r['assembly_key'] / 'artifacts' / r['executable_sha256']

def logged(name, argv, env=ENV):
    start = time.perf_counter_ns()
    with (O / (name + '.log')).open('w') as f:
        p = subprocess.run(argv, env=env, stdout=f, stderr=subprocess.STDOUT, timeout=1800)
    ms = (time.perf_counter_ns() - start) / 1e6
    assert p.returncode == 0, (name, p.returncode)
    return ms
