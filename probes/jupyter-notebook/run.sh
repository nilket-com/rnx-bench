#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONDONTWRITEBYTECODE=1
out=results/jupyter-0047-notebook
mkdir -p "$out"
cargo build --release --locked --manifest-path ../rnx/jupyter/Cargo.toml --features transport-probe --example worker-probe --example transport-probe
cargo build --release --locked --manifest-path ../rnx/jupyter/Cargo.toml --bin rnx-jupyter
cargo test --locked --manifest-path ../rnx/jupyter/Cargo.toml > "$out/kernel-tests.txt" 2> "$out/kernel-tests-stderr.txt"
cargo test --locked --manifest-path ../rnx/jupyter/Cargo.toml --features transport-probe > "$out/kernel-probe-tests.txt" 2> "$out/kernel-probe-tests-stderr.txt"
cargo clippy --locked --manifest-path ../rnx/jupyter/Cargo.toml --all-targets --features transport-probe -- -D warnings > "$out/clippy.txt" 2>&1
probes/jupyter-notebook/.venv/bin/python - <<'PY'
import hashlib,importlib.metadata,json,os,pathlib,subprocess
root=pathlib.Path.cwd();out=root/'results/jupyter-0047-notebook'
py='probes/jupyter-notebook/.venv/bin/python'
results=[]
for suffix in ['', '-confirmation']:
 for name in ['install','status','notebook','browser']:
  command=[py,'probes/jupyter-notebook/'+name+'.py']
  with (out/(name+suffix+'.jsonl')).open('w') as stdout,(out/(name+suffix+'-stderr.txt')).open('w') as stderr:
   r=subprocess.run(command,stdout=stdout,stderr=stderr,timeout=150)
  results.append(dict(command=command,run=name+suffix,exit=r.returncode));(out/'exit-status.json').write_text(json.dumps(results,indent=2)+'\n')
  print(name+suffix,r.returncode,flush=True)
  if r.returncode:raise SystemExit(r.returncode)
# The original supervision fixtures, redirected so accepted evidence is unchanged.
regression=out/'supervision';regression.mkdir(exist_ok=True)
for name in ['probe','extended','boundaries','notebook']:
 command=[py,'probes/jupyter-supervision/'+name+'.py']
 with (regression/(name+'.jsonl')).open('w') as stdout,(regression/(name+'-stderr.txt')).open('w') as stderr:
  r=subprocess.run(command,stdout=stdout,stderr=stderr,timeout=180,env={**os.environ,'RNX_JUPYTER_RESULTS':str(regression)})
 results.append(dict(command=command,run='supervision-'+name,exit=r.returncode));(out/'exit-status.json').write_text(json.dumps(results,indent=2)+'\n')
 print('supervision-'+name,r.returncode,flush=True)
 if r.returncode:raise SystemExit(r.returncode)
wire=out/'wire';wire.mkdir(exist_ok=True)
for name in ['probe','extended']:
 command=[py,'probes/jupyter-zmtp/'+name+'.py']
 with (wire/(name+'.jsonl')).open('w') as stdout,(wire/(name+'-stderr.txt')).open('w') as stderr:
  r=subprocess.run(command,stdout=stdout,stderr=stderr,timeout=60,env={**os.environ,'RNX_ZMTP_RESULTS':str(wire),'RNX_ZMTP_BINARY':str(root.parent/'rnx/jupyter/target/release/examples/transport-probe')})
 results.append(dict(command=command,run='wire-'+name,exit=r.returncode));(out/'exit-status.json').write_text(json.dumps(results,indent=2)+'\n')
 print('wire-'+name,r.returncode,flush=True)
 if r.returncode:raise SystemExit(r.returncode)
for name in ['timing','startup']:
 with (out/(name+'.txt')).open('w') as stdout,(out/(name+'-stderr.txt')).open('w') as stderr:
  command=['taskset','-c','4',py,'probes/jupyter-notebook/'+name+'.py']
  r=subprocess.run(command,stdout=stdout,stderr=stderr,timeout=180)
 results.append(dict(command=command,run=name,exit=r.returncode));(out/'exit-status.json').write_text(json.dumps(results,indent=2)+'\n')
 print(name,r.returncode,flush=True)
 if r.returncode:raise SystemExit(r.returncode)
commands=[['rustc','--version'],['cargo','--version'],['uname','-a'],['ldd','../rnx/jupyter/target/release/rnx-jupyter']]
with (out/'versions.txt').open('w') as f:
 for command in commands:
  r=subprocess.run(command,capture_output=True,text=True,check=True);f.write('$ '+' '.join(command)+'\n'+r.stdout+'\n')
 f.write('\n'.join(sorted(d.metadata['Name']+'=='+d.version for d in importlib.metadata.distributions()))+'\n')
paths=list(pathlib.Path('../rnx/jupyter/src').glob('*.rs'))+[pathlib.Path('../rnx/jupyter/Cargo.toml'),pathlib.Path('../rnx/jupyter/Cargo.lock'),pathlib.Path('../rnx/jupyter/target/release/rnx-jupyter'),pathlib.Path('../rnx/target/release/rnx')]
(out/'sha256.json').write_text(json.dumps({str(p):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths},indent=2)+'\n')
PY
cargo fmt --check --manifest-path ../rnx/jupyter/Cargo.toml
python3 ../rnx/jupyter/scripts/third-party-notices.py --check
cargo check --locked --manifest-path ../rnx/jupyter/Cargo.toml --target x86_64-pc-windows-msvc > "$out/windows-check.txt" 2>&1
