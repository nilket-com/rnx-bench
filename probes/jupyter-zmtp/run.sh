#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p results/jupyter-zmtp-0048-extension
cargo build --release --locked --manifest-path probes/jupyter-zmtp/Cargo.toml
cargo test --locked --manifest-path probes/jupyter-zmtp/Cargo.toml > results/jupyter-zmtp-0048-extension/rust-tests.txt 2> results/jupyter-zmtp-0048-extension/rust-tests-stderr.txt
python3 - <<'PY'
import json, subprocess
from pathlib import Path
out=Path('results/jupyter-zmtp-0048-extension')
python='probes/jupyter-transport/.venv/bin/python'
results=[]
for suffix in ['', '-confirmation']:
    for name,file in [('transport','probe.py'),('extended','extended.py')]:
        cmd=[python,'probes/jupyter-zmtp/'+file]
        with (out/(name+suffix+'.jsonl')).open('w') as stdout,(out/(name+suffix+'-stderr.txt')).open('w') as stderr:
            r=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=45)
        results.append({'command':cmd,'run':name+suffix,'exit':r.returncode})
        (out/'exit-status.json').write_text(json.dumps(results,indent=2)+'\n')
        if r.returncode:raise SystemExit(r.returncode)
PY
cargo fmt --check --manifest-path probes/jupyter-zmtp/Cargo.toml
