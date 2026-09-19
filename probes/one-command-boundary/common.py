from pathlib import Path
import os, json, subprocess, time, hashlib
B=Path(__file__).resolve().parents[2];P=Path(__file__).resolve().parent;T=P/'target';O=B/'results/one-command-boundary-0067';R=B.parent/'rnx'
BASE=subprocess.check_output(['git','-C',str(R),'rev-parse','9570b25']).decode().strip()
ENV={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','CARGO_','RNX_','RUSTFLAGS','RUSTC_'))}
ENV.update(CARGO_HOME=str(T/'cargo-home'),CARGO_BUILD_JOBS='4')
O.mkdir(parents=True,exist_ok=True)
def save(name,value): (O/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def run(args,*,cwd=None,env=None,ok=True,timeout=900,data=None):
 start=time.monotonic();p=subprocess.run(list(map(str,args)),cwd=cwd,env=env or ENV,input=data,capture_output=True,timeout=timeout)
 with (O/'commands.jsonl').open('a') as f:f.write(json.dumps({'args':list(map(str,args)),'cwd':str(cwd) if cwd else None,'status':p.returncode,'seconds':time.monotonic()-start,'stderr':p.stderr.decode(errors='replace')[-12000:]})+'\n')
 if ok and p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-9000:])
 return p

def git(root,*args,**kw):return run(['git','-C',root,'-c','commit.gpgsign=false',*args],**kw)
def sha(data):return hashlib.sha256(data).hexdigest()
