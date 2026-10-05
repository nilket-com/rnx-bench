import subprocess,time,json,pathlib
out=pathlib.Path(__file__).resolve().parents[2]/'results/lua-rust-0001';out.mkdir(parents=True,exist_ok=True)
assert not (out/'builds.json').exists(), 'refuse overwrite'
assert not pathlib.Path('/tmp/lua-rust-0001/piccolo/target').exists()
assert not pathlib.Path('/tmp/lua-rust-0001/omni-target').exists()
steps=[('piccolo',['cargo','build','--release','--locked','--example','interpreter'],'/tmp/lua-rust-0001/piccolo'),('omnilua',['cargo','install','omnilua-cli','--version','0.7.1','--locked','--root','/tmp/lua-rust-0001/install','--target-dir','/tmp/lua-rust-0001/omni-target'],'/tmp/lua-rust-0001')]
rows=[]
for name,cmd,cwd in steps:
 t=time.monotonic();r=subprocess.run(cmd,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);elapsed=time.monotonic()-t
 (out/(name+'-build.txt')).write_bytes(r.stdout);rows.append(dict(name=name,command=cmd,cwd=cwd,seconds=elapsed,status=r.returncode));(out/'builds.json').write_text(json.dumps(rows,indent=2)+'\n');print(name,elapsed,r.returncode,flush=True)
 if r.returncode:raise SystemExit(r.returncode)
