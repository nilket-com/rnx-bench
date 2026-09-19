from pathlib import Path
import os,sys,json,time,hashlib,subprocess,shutil,importlib.util
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;B=P.parents[1];R=B.parent/'rnx';T=P/'target';O=B/'results/one-install-0067'
REV='7ae886305aea33312a061cbafbebbb49ff8bc8c4';URL='https://github.com/nilket-com/rnx'
BASE={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','CARGO_','RUST','RNX_','POLARS_','XDG_','JUPYTER','IPYTHON'))}
BASE.update(PYTHONDONTWRITEBYTECODE='1',POLARS_MAX_THREADS='1',TERM='xterm-256color')
def save(name,v):(O/name).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(args,env=BASE,cwd=None,ok=True,timeout=1800):
 start=time.monotonic();p=subprocess.run(list(map(str,args)),env=env,cwd=cwd,capture_output=True,timeout=timeout)
 with (O/'commands.jsonl').open('a') as f:f.write(json.dumps({'args':list(map(str,args)),'cwd':str(cwd) if cwd else None,'status':p.returncode,'seconds':time.monotonic()-start,'stderr':p.stderr.decode(errors='replace')[-16000:]})+'\n')
 if ok and p.returncode:raise RuntimeError((args,p.returncode,p.stderr.decode(errors='replace')[-16000:]))
 return p

def git(root,*args):return run(['git','--no-pager','-c','color.ui=false','-C',root,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null',*args])
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def environment(kind):
 d=json.loads((T/kind/'setup.json').read_text());return d,{**BASE,**d['env']}
