from pathlib import Path
import os,sys,json,time,subprocess,shutil,hashlib,importlib.util
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;B=P.parents[1];R=B.parent/'rnx';T=P/'target';O=B/'results/one-install-final-0067'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','RNX_','CARGO_','RUST','POLARS_'))}
ENV.update(PYTHONDONTWRITEBYTECODE='1',POLARS_MAX_THREADS='1',TERM='xterm-256color',RNX_CONFIG=str(T/'no-config'),RNX_HISTORY=str(T/'history'))
def save(name,x):(O/name).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(args,cwd=R,env=ENV,ok=True,timeout=2400):
 start=time.monotonic();p=subprocess.run(list(map(str,args)),cwd=cwd,env=env,capture_output=True,timeout=timeout)
 with (O/'commands.jsonl').open('a') as f:f.write(json.dumps({'args':list(map(str,args)),'cwd':str(cwd),'status':p.returncode,'seconds':time.monotonic()-start})+'\n')
 if ok and p.returncode:raise RuntimeError((args,p.stderr.decode(errors='replace')[-8000:]))
 return p
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
