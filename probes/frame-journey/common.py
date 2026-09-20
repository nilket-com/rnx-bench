"""Shared paths and helpers for the 0068 gate 3 journey probe (product at PRODUCT_REV)."""
import hashlib, json, os, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True
H = Path(__file__).resolve().parent
B = H.parents[1]
R = B.parent / 'rnx'
O = B / 'results/frame-journey-0068'
T = H / 'target'
PRODUCT_REV = 'a8e0f4e'
PRODUCT = T / 'product'
ENV = {k: v for k, v in os.environ.items() if not k.startswith(('CARGO_', 'RUST', 'RNX_', 'POLARS_', 'JUPYTER', 'IPYTHON'))}
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


RNX = PRODUCT / 'target/release/rnx'
KERNEL = PRODUCT / 'jupyter/target/release/rnx-jupyter'
SALES = 'region,item,qty,price\nwest,apple,3,1.5\nwest,pear,1,2.0\neast,apple,5,1.5\neast,plum,2,3.0\nnorth,apple,4,1.5\n'
SALES_SCHEMA = '[("region","string"),("item","string"),("qty","i64"),("price","f64")]'
WIDE_HEADER = ','.join(f'c{i}' for i in range(12))
WIDE_ROWS = '\n'.join(','.join(str(r * 100 + c) for c in range(12)) for r in range(15))
WIDE_SCHEMA = '[' + ','.join(f'("c{i}","i64")' for i in range(12)) + ']'
