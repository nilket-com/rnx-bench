import hashlib,json,pathlib,subprocess,time
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2]/'rnx';OUT=HERE.parents[1]/'results/polars-cost-0058';OUT.mkdir(exist_ok=True)
TARGET=HERE/'target/cold'
assert not TARGET.exists(),'first build requires an absent target; use a new target or explicitly remove this fixture cache'
cmd=['cargo','build','--release','--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'adapters/polars/Cargo.toml'),'--target-dir',str(TARGET)]
results={'rust_downloads':'cached registry and crate source; no network','jobs':2,'command':cmd}
for name in ['cold','warm']:
 start=time.perf_counter_ns()
 with (OUT/('build-'+name+'.log')).open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 elapsed=(time.perf_counter_ns()-start)/1e9
 assert r.returncode==0,name
 results[name+'_seconds']=elapsed;print(name,elapsed,flush=True)
exe=TARGET/'release/rnx-polars';results['binary_bytes']=exe.stat().st_size;results['sha256']=hashlib.sha256(exe.read_bytes()).hexdigest()
venv=HERE/'target/python';assert not venv.exists()
start=time.perf_counter_ns();subprocess.run(['uv','venv','--python','3.14',str(venv)],check=True,capture_output=True)
results['python_venv_seconds']=(time.perf_counter_ns()-start)/1e9
wheels=HERE.parent/'polars-boundary/wheels';cmd=['uv','pip','install','--python',str(venv/'bin/python'),'--no-index',*map(str,sorted(wheels.glob('*.whl')))]
start=time.perf_counter_ns()
with (OUT/'python-install.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
assert r.returncode==0;results['python_install_seconds']=(time.perf_counter_ns()-start)/1e9
results['python_wheels']='local exact wheels verified at gate 1; no network'
(OUT/'setup.json').write_text(json.dumps(results,indent=2)+'\n');print('setup complete',flush=True)
