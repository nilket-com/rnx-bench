#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONDONTWRITEBYTECODE=1
out=results/jupyter-0047-supervision
mkdir -p "$out"
cargo build --release --locked --manifest-path ../rnx/jupyter/Cargo.toml --features transport-probe --bin rnx-jupyter --example worker-probe --example transport-probe
cargo test --locked --manifest-path ../rnx/jupyter/Cargo.toml > "$out/rust-tests.txt" 2> "$out/rust-tests-stderr.txt"
cargo test --locked --manifest-path ../rnx/jupyter/Cargo.toml --features transport-probe > "$out/rust-probe-tests.txt" 2> "$out/rust-probe-tests-stderr.txt"
probes/jupyter-transport/.venv/bin/python - <<'PY'
import hashlib,json,os,pathlib,subprocess
out=pathlib.Path('results/jupyter-0047-supervision').resolve()
(out/'kernel-stderr.txt').write_text('')
results=[]
for suffix in ['', '-confirmation']:
    for name in ['probe','extended','boundaries','notebook']:
        command=['probes/jupyter-transport/.venv/bin/python','probes/jupyter-supervision/'+name+'.py']
        with (out/(name+suffix+'.jsonl')).open('w') as stdout,(out/(name+suffix+'-stderr.txt')).open('w') as stderr:
            r=subprocess.run(command,stdout=stdout,stderr=stderr,timeout=180)
        results.append(dict(command=command,run=name+suffix,exit=r.returncode))
        (out/'exit-status.json').write_text(json.dumps(results,indent=2)+'\n')
        print(name+suffix,r.returncode,flush=True)
        if r.returncode:raise SystemExit(r.returncode)
    wire=out/('wire'+suffix);wire.mkdir(exist_ok=True)
    env={**os.environ,'RNX_ZMTP_RESULTS':str(wire),'RNX_ZMTP_BINARY':str(pathlib.Path('../rnx/jupyter/target/release/examples/transport-probe').resolve())}
    for name in ['probe','extended']:
        command=['probes/jupyter-transport/.venv/bin/python','probes/jupyter-zmtp/'+name+'.py']
        with (wire/(name+'.jsonl')).open('w') as stdout,(wire/(name+'-stderr.txt')).open('w') as stderr:
            r=subprocess.run(command,env=env,stdout=stdout,stderr=stderr,timeout=60)
        results.append(dict(command=command,run='wire-'+name+suffix,exit=r.returncode))
        (out/'exit-status.json').write_text(json.dumps(results,indent=2)+'\n')
        print('wire-'+name+suffix,r.returncode,flush=True)
        if r.returncode:raise SystemExit(r.returncode)
commands=[['rustc','--version'],['cargo','--version'],['uname','-a'],['probes/jupyter-transport/.venv/bin/python','-c',"import importlib.metadata as m;print(*sorted(d.metadata['Name']+'=='+d.version for d in m.distributions()),sep=chr(10))"],['git','-C','../rnx','rev-parse','HEAD'],['git','rev-parse','HEAD'],['ldd','../rnx/jupyter/target/release/rnx-jupyter']]
with (out/'versions.txt').open('w') as f:
 for command in commands:
  r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,check=True);f.write('$ '+' '.join(command)+'\n'+r.stdout+'\n')
paths=[pathlib.Path('../rnx/target/release/rnx'),pathlib.Path('../rnx/jupyter/target/release/rnx-jupyter')]
paths+=list(pathlib.Path('../rnx/jupyter/src').glob('*.rs'))+[pathlib.Path('../rnx/jupyter/Cargo.toml'),pathlib.Path('../rnx/jupyter/Cargo.lock')]
(out/'source-and-binary-sha256.json').write_text(json.dumps({str(p):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths},indent=2)+'\n')
PY
cargo fmt --check --manifest-path ../rnx/jupyter/Cargo.toml
python3 ../rnx/jupyter/scripts/third-party-notices.py --check
cargo check --locked --target x86_64-pc-windows-msvc --manifest-path ../rnx/jupyter/Cargo.toml > "$out/windows-check.txt" 2>&1
