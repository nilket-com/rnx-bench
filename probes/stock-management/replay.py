"""Replay accepted lifecycle matrices through both real management frontends."""
from pathlib import Path
import hashlib,json,subprocess as sp,sys,time
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/stock-management-0067';W=H/'target'
mode,group=sys.argv[1:];assert mode in ['stock','compat'];assert group in ['preparation','startup','commit']
label=mode+'-'+group;out=O/label;out.mkdir(exist_ok=True);rows=[]
def replay(file):
 p=B/'probes'/('session-'+group)/file;raw=p.read_text();s=raw
 s=s.replace("W=H/'target'",'W=Path('+repr(str(W/label))+')')
 s=s.replace('results/session-'+group+'-0063','results/stock-management-0067/'+label)
 s=s.replace("R/'tools/project/target/debug/rnx-project'", 'Path('+repr(str(W/('rnx' if mode=='stock' else 'rnx-project')))+')')
 s=s.replace("R/'target/debug/rnx'", 'Path('+repr(str(W/'rnx'))+')')
 s=s.replace("r['executable_sha256']", "r['executable_blake3']")
 s=s.replace("hashlib.sha256(assembly['identity'].encode()).hexdigest()", "subprocess.check_output(["+repr(str(W/'b3'))+"],input=assembly['identity'].encode()).decode().strip()")
 s=s.replace('project-sources=["actual/project-sources"]', 'project-sources=["actual/project-sources"]\ncount-allocations=["actual/count-allocations"]')
 s=s.replace('actual={{package="rnx",path=', 'actual={{package="rnx",default-features=false,path=')
 s=s.replace("env.update(PYTHONDONTWRITEBYTECODE='1',", "env.update(XDG_DATA_HOME=str(W/'data'),PYTHONDONTWRITEBYTECODE='1',")
 if mode=='stock':
  for command in ['lock','build','session','eval','add']:
   s=s.replace("[T,'"+command+"'", "[T,'project','"+command+"'")
  s=s.replace('[T,*args,', "[T,'project',*args,")
  s=s.replace("assert k==8 and 'export RNX_DEP_RUNTIME=/absolute/path/to/rnx' in e[1]", "assert (k==8 and 'default runtime coordinates refused:' in e[1] and 'export RNX_DEP_RUNTIME=' in e[1]) or (k==2 and 'Runtime: Git ' in e[2] and ('not yet confirmed reachable' in e[2] or 'acquired;' in e[2]))")
  s=s.replace("rows['scratch_missing_runtime_exact_setup_refusal']=True", "rows['scratch_default_coordinates_classified_without_fetch']={'kind':k,'reply':e}")
 else:
  s=s.replace("'export RNX_DEP_RUNTIME=/absolute/path/to/rnx' in e[1]", "\"runtime install --from '/path/to/rnx'\" in e[1]")
 dest=O/'scripts'/(label+'-'+file);dest.write_text(s)
 dest.with_suffix('.json').write_text(json.dumps(dict(original=str(p.relative_to(B)),original_sha256=hashlib.sha256(raw.encode()).hexdigest(),effective_sha256=hashlib.sha256(s.encode()).hexdigest()),indent=2)+'\n')
 loader='import sys;sys.dont_write_bytecode=True;exec(compile(open(sys.argv[1]).read(),sys.argv[2],"exec"),{"__name__":"__main__","__file__":sys.argv[2]})'
 start=time.monotonic()
 with (out/(file+'.log')).open('w') as f:r=sp.run([sys.executable,'-c',loader,str(dest),str(p)],stdout=f,stderr=sp.STDOUT,timeout=1800,cwd=B)
 rows.append(dict(driver=file,status=r.returncode,seconds=time.monotonic()-start));(out/'checks.json').write_text(json.dumps(rows,indent=2)+'\n');print(label,file,r.returncode,flush=True);assert r.returncode==0,out/(file+'.log')
assert not (W/label).exists(), 'fresh group target required; do not resume partial matrices'
replay('setup.py')
replay('check.py')
