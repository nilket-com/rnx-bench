"""Shared paths and helpers for the 0068 gate 1 presentation-seam probe."""
import hashlib, json, os, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True
H = Path(__file__).resolve().parent
B = H.parents[1]
R = B.parent / 'rnx'
O = B / 'results/frame-seam-0068'
T = H / 'target'
BASELINE_REV = 'b5664ff'
ENV = {k: v for k, v in os.environ.items() if not k.startswith(('CARGO_', 'RUST', 'RNX_', 'POLARS_'))}
ENV.update(POLARS_MAX_THREADS='1', TERM='xterm-256color', PYTHONDONTWRITEBYTECODE='1')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def save(name, value):
    O.mkdir(parents=True, exist_ok=True)
    (O / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def run(argv, cwd=None, timeout=600, check=True, env=None, input=None):
    p = subprocess.run([str(a) for a in argv], cwd=cwd, env=env or ENV, capture_output=True,
                       timeout=timeout, input=input)
    if check and p.returncode != 0:
        raise SystemExit(f'{argv[0]} failed ({p.returncode}):\n{p.stdout.decode(errors="replace")[-3000:]}\n{p.stderr.decode(errors="replace")[-3000:]}')
    return p


def tool(kind):
    return {
        'candidate': T / 'candidate/tools/project/target/release/rnx-project',
        'candidate-probe': T / 'candidate/tools/project/target/debug/rnx-project-assembly-probe',
        'baseline': T / 'baseline-tool/release/rnx-project',
    }[kind]
