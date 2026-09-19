"""Gate 3 drives the product; targets are disposable, evidence is retained."""
from pathlib import Path
import os, subprocess, json, time, hashlib
P=Path(__file__).resolve().parent;B=P.parents[1];R=B.parent/'rnx';T=P/'target';O=B/'results/git-source-workflow-0067'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','RNX_','CARGO_','RUST'))}
ENV.update(CARGO_HOME=str(T/'cargo-home'),RNX_PROJECT_CACHE=str(T/'cache'),XDG_STATE_HOME=str(T/'state'),XDG_DATA_HOME=str(T/'data'),POLARS_MAX_THREADS='1')
TOOL=T/'rnx-project';PROBE=T/'assembly-probe'
def run(args,*,env=None,cwd=None,data=None,ok=True,timeout=1200):
 start=time.monotonic();p=subprocess.run(list(map(str,args)),env=env or ENV,cwd=cwd,input=data,capture_output=True,timeout=timeout)
 with (O/'commands.jsonl').open('a') as f:f.write(json.dumps({'args':list(map(str,args)),'cwd':str(cwd) if cwd else None,'seconds':time.monotonic()-start,'status':p.returncode,'stderr':p.stderr.decode(errors='replace')[-12000:]})+'\n')
 if ok and p.returncode:raise RuntimeError(f'{args}: {p.stderr.decode(errors="replace")[-12000:]}')
 return p

def save(name,value):(O/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def git(root,*args,**kwargs):return run(['git','--no-pager','-c','color.ui=false','-C',root,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null',*args],**kwargs)
def sha(b):return hashlib.sha256(b).hexdigest()
def project(name,url,rev,natives=()):
 p=T/name;p.mkdir();(p/'main.rn').write_text('pub fn main(_) { println!("application"); }\n')
 (p/'rnx.toml').write_text(f'format=2\n[application]\nentry="main.rn"\n[runtime]\ngit={json.dumps(url)}\nrev="{rev}"\n')
 if natives:run([TOOL,'add','--manifest',p/'rnx.toml',*natives])
 return p
