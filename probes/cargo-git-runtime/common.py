from pathlib import Path
import json, os, subprocess, time, hashlib
B = Path(__file__).resolve().parents[2]
P = Path(__file__).resolve().parent
T = P / 'target'
O = B / 'results/cargo-git-runtime-0067'
REV = '94f5f3f98ba756c5ab5293d1e5132c7fd7b52d32'
URL = 'https://github.com/nilket-com/rnx'
ENV = {k:v for k,v in os.environ.items() if not k.startswith(('GIT_', 'CARGO_', 'RNX_', 'RUSTFLAGS', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER'))}
ENV.update(CARGO_HOME=str(T/'cargo-home'), CARGO_BUILD_JOBS='4', POLARS_MAX_THREADS='1')
O.mkdir(parents=True, exist_ok=True)
def save(name, value):
    (O/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
def run(args, *, cwd=None, env=None, data=None, ok=True, timeout=600):
    start=time.monotonic()
    p=subprocess.run(list(map(str,args)),cwd=cwd,env=env or ENV,input=data,capture_output=True,timeout=timeout)
    with (O/'commands.jsonl').open('a') as f:
        f.write(json.dumps({'args':list(map(str,args)), 'cwd':str(cwd) if cwd else None,'seconds':time.monotonic()-start,'status':p.returncode,'stderr':p.stderr.decode(errors='replace')[-10000:]})+'\n')
    if ok and p.returncode: raise RuntimeError(f'{args}: {p.stderr.decode(errors="replace")[-8000:]}')
    return p

def git(root,*args,**kwargs):
    env=ENV | {'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null','GIT_CONFIG_NOSYSTEM':'1','GIT_ATTR_NOSYSTEM':'1','GIT_OPTIONAL_LOCKS':'0','GIT_NO_REPLACE_OBJECTS':'1'}
    return run(['git','-C',root,'-c','core.autocrlf=false','-c','core.fsmonitor=false','-c','core.hooksPath=/dev/null','-c','core.attributesFile=/dev/null',*args],env=env,**kwargs)

def sha(data): return hashlib.sha256(data).hexdigest()
