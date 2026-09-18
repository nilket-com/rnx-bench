"""Fresh same-content checkout/installed controls; four actual cold assemblies."""
from pathlib import Path
import os,sys,json,subprocess as sp,shutil,time,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/runtime-cost-0064'
assert not W.exists();W.mkdir();O.mkdir(exist_ok=True);C=W/'checkout';C.mkdir()
E={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','GIT_','CARGO_','RUST','POLARS_'))};E.update(RNX_PROJECT_CACHE=str(W/'cache'),XDG_DATA_HOME=str(W/'data'),XDG_STATE_HOME=str(W/'state'),RNX_CONFIG=str(W/'absent-config'),RNX_HISTORY=str(W/'history'),TERM='xterm-256color',POLARS_MAX_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
def call(args,timeout=600):
 t=time.perf_counter();p=sp.run(list(map(str,args)),env=E,cwd=W,capture_output=True,text=True,timeout=timeout);elapsed=time.perf_counter()-t;assert p.returncode==0,(args,p.stdout,p.stderr);return p,elapsed
base=sp.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();assert not sp.check_output(['git','status','--porcelain'],cwd=R)
for n in sp.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0'):
 if n:d=C/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/n,d)
call(['git','init','-q',C]);call(['git','-C',C,'add','.']);call(['git','-C',C,'-c','user.name=Fixture','-c','user.email=f@invalid','-c','commit.gpgsign=false','commit','-qm','runtime cost snapshot'])
# The source is preserved by published baseline; no product instrumentation here.
p,t=call(['cargo','build','--release','--locked','--offline','--manifest-path',C/'tools/project/Cargo.toml','--target-dir',W/'tool-build']);(O/'tool-build.log').write_text(p.stdout+p.stderr);T=W/'tool-build/release/rnx-project'
p,t=call([T,'runtime','install','--from',C]);(O/'install.log').write_text(p.stdout+p.stderr);id=p.stdout.split('runtime ',1)[1].splitlines()[0];I=W/'data/rnx/runtimes/entries'/id/'source';doc=json.loads((I.parent/'installation.json').read_text());assert doc['tool_sha256']==hashlib.sha256(T.read_bytes()).hexdigest()
state=dict(baseline=base,checkout=str(C),installed=str(I),tool=str(T),env=E,initial_install_seconds=t,installation=doc,cells=[]);(W/'setup.json').write_text(json.dumps(state,indent=2)+'\n')
print('PASS cost snapshot and installation ready',flush=True)
