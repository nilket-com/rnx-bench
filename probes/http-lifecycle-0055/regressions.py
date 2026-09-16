#!/usr/bin/env python3
"""Reproduce existing fixtures without overwriting their historical results."""
import os,pathlib,subprocess,sys
sys.dont_write_bytecode=True
os.environ["PYTHONDONTWRITEBYTECODE"]="1"
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/http-lifecycle-0055';OUT.mkdir(exist_ok=True,parents=True)
def run(args,env=None):subprocess.run(list(map(str,args)),cwd=ROOT,env=env,check=True,timeout=180)
run(['cargo','build','--release','--locked','--offline','--manifest-path','probes/extensions/Cargo.toml'])
(OUT/'extension-assembly').mkdir(exist_ok=True)
run([sys.executable,'probes/extensions/check.py','probes/extensions/target/release/app'],dict(os.environ,RNX_EXTENSION_RESULTS=str(OUT/'extension-assembly')))
p=ROOT/'probes/extensions/lifecycle.py'
s=p.read_text().replace("ROOT/'results/lifecycle-0053'", "ROOT/'results/http-lifecycle-0055/extensions'")
exec(compile(s,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
run(['cargo','build','--release','--locked','--offline','--manifest-path','probes/postgres/ownership/Cargo.toml'])
run([sys.executable,'probes/postgres/ownership.py'],dict(os.environ,RNX_PG_OWNERSHIP_OUT=str(OUT/'postgres')))
(OUT/'kernel').mkdir(exist_ok=True)
for name in ['probe','extended']:
    with (OUT/'kernel'/f'{name}.jsonl').open('w') as log, (OUT/'kernel'/f'{name}-stderr.txt').open('w') as errors:
        subprocess.run([str(ROOT/'probes/jupyter-transport/.venv/bin/python'),str(ROOT/f'probes/jupyter-supervision/{name}.py')],cwd=ROOT,env=dict(os.environ,RNX_JUPYTER_RESULTS=str(OUT/'kernel')),stdout=log,stderr=errors,check=True,timeout=180)
