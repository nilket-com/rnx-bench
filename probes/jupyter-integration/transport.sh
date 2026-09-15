#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=results/jupyter-0047-integration
mkdir -p "$out"
cargo build --release --locked --manifest-path ../rnx/jupyter/Cargo.toml --features transport-probe --example transport-probe
cargo test --locked --manifest-path ../rnx/jupyter/Cargo.toml > "$out/rust-tests.txt" 2> "$out/rust-tests-stderr.txt"
cargo test --locked --manifest-path ../rnx/jupyter/Cargo.toml --features transport-probe > "$out/rust-probe-tests.txt" 2> "$out/rust-probe-tests-stderr.txt"
probes/jupyter-transport/.venv/bin/python - <<'PY'
import os,json,subprocess
from pathlib import Path
out=Path('results/jupyter-0047-integration').resolve()
env=os.environ.copy()
env['RNX_ZMTP_BINARY']=str(Path('../rnx/jupyter/target/release/examples/transport-probe').resolve())
env['RNX_ZMTP_RESULTS']=str(out)
results=[]
for suffix in ['', '-confirmation']:
    for name,file in [('transport','probe.py'),('extended','extended.py')]:
        command=['probes/jupyter-transport/.venv/bin/python','probes/jupyter-zmtp/'+file]
        with (out/(name+suffix+'.jsonl')).open('w') as stdout,(out/(name+suffix+'-stderr.txt')).open('w') as stderr:
            r=subprocess.run(command,env=env,stdout=stdout,stderr=stderr,timeout=45)
        results.append({'command':command,'run':name+suffix,'exit':r.returncode})
        (out/'exit-status.json').write_text(json.dumps(results,indent=2)+'\n')
        if r.returncode:raise SystemExit(r.returncode)
PY
cargo fmt --check --manifest-path ../rnx/jupyter/Cargo.toml
cargo check --locked --target x86_64-pc-windows-msvc --manifest-path ../rnx/jupyter/Cargo.toml > "$out/windows-check.txt" 2>&1
