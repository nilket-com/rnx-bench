"""Current-product regression; redirect fixtures, archive edits, preserve old evidence."""
from pathlib import Path
import hashlib,json,os,subprocess as sp,sys,time
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/removal-final-0066';W=H/'target'
W.mkdir(exist_ok=True);(O/'scripts').mkdir(exist_ok=True)
rows=[]
def command(name,args,cwd=B,env=None):
 start=time.monotonic()
 with (O/(name+'.log')).open('w') as f:p=sp.run(list(map(str,args)),cwd=cwd,env=env,stdout=f,stderr=sp.STDOUT,timeout=1800)
 rows.append(dict(name=name,command=list(map(str,args)),status=p.returncode,seconds=time.monotonic()-start))
 (O/(sys.argv[1]+'-checks.json')).write_text(json.dumps(rows,indent=2)+'\n');print(name,p.returncode,flush=True);assert p.returncode==0,name

def replay(relative,group,old_result,extra=lambda s:s):
 p=B/'probes'/relative;s=p.read_text();raw=s
 s=s.replace("W=H/'target'",'W=Path('+repr(str(W/group))+')')
 s=s.replace('results/'+old_result,'results/removal-final-0066/'+group)
 s=s.replace("r['executable_sha256']", "r['executable_blake3']").replace("tool_sha256='x'", "tool_blake3='x'")
 if relative=='session-preparation/check.py':
  s=s.replace("hashlib.sha256(assembly['identity'].encode()).hexdigest()", "subprocess.check_output(["+repr(str(W/'b3'))+"],input=assembly['identity'].encode()).decode().strip()")
 if relative=='runtime-discovery/check.py':
  s=s.replace('dict(format=1,id=aid,extra=True)', 'dict(format=2,id=aid,extra=True)').replace('dict(format=2,id=aid)', 'dict(format=99,id=aid)')
 s=extra(s)
 out=O/group;out.mkdir(exist_ok=True)
 dest=O/'scripts'/(group+'-'+relative.replace('/','-'));dest.write_text(s)
 (dest.with_suffix('.json')).write_text(json.dumps(dict(original=relative,sha256=hashlib.sha256(raw.encode()).hexdigest(),effective_sha256=hashlib.sha256(s.encode()).hexdigest()),indent=2)+'\n')
 loader='import sys;sys.dont_write_bytecode=True;exec(compile(open(sys.argv[1]).read(),sys.argv[2],"exec"),{"__name__":"__main__","__file__":sys.argv[2]})'
 command(group+'-'+relative.replace('/','-'),[sys.executable,'-c',loader,dest,p])

def build(root,features=()):
 command(('root' if root==R else 'tool')+'-build-'+('-'.join(features) or 'default'),['cargo','build','--locked','--offline','--manifest-path',root/'Cargo.toml',*( ['--features',','.join(features)] if features else [])],R)

phase=sys.argv[1]
if phase=='contracts':
 build(R);build(R/'tools/project',['test-support'])
 for group in ['preparation','startup']:
  assert not (W/group).exists(),W/group
  def adjust(s):
   s=s.replace('export RNX_DEP_RUNTIME=/absolute/path/to/rnx','rnx-project runtime install --from /path/to/rnx')
   # Current missing-runtime refusal; isolate the installation store from the host.
   s=s.replace("env.update(PYTHONDONTWRITEBYTECODE='1',", "env.update(XDG_DATA_HOME=str(W/'data'),PYTHONDONTWRITEBYTECODE='1',")
   return s
  for file in ['setup.py','check.py']:
   replay('session-'+group+'/'+file,group,'session-'+group+'-0063',adjust)
 build(R,['test-support'])
 assert not (W/'commit').exists()
 for file in ['setup.py','check.py']:replay('session-commit/'+file,'commit','session-commit-0063')
 build(R)
 assert not (W/'discovery').exists()
 replay('runtime-discovery/check.py','discovery','runtime-discovery-0064')
 replay('runtime-discovery/reopen.py','discovery','runtime-discovery-0064')
 replay('runtime-publication/check.py','publication','runtime-publication-0064')
 for support in [True,False]:
  label='repair-support' if support else 'repair-ordinary'
  if not support:
   command('tool-release',['cargo','build','--locked','--offline','--release','--manifest-path',R/'tools/project/Cargo.toml','--bin','rnx-project'],R)
  def repair(s):
   s=s.replace("W=Path(os.environ.get('RNX_REPAIR_TARGET',H/'repair-target'))",'W=Path('+repr(str(W/label))+')')
   if not support:s=s.replace("R/'tools/project/target/debug/rnx-project'","R/'tools/project/target/release/rnx-project'")
   s=s.replace("assert snapshot(entry)==before;assert", "if what=='blob':assert 'corrupt installed runtime' in r.stderr and 'install Git if missing' not in r.stderr,r.stderr\n  assert snapshot(entry)==before;assert")
   needle="(O/os.environ.get('RNX_REPAIR_RESULT','repair.json')).write_text"
   extra="""# Missing Git still gets prerequisite guidance and changes no state.
empty=W/'empty-path';empty.mkdir();before=snapshot(entry)
p=sp.run([str(T),'runtime','select',id],env=dict(E,PATH=str(empty)),capture_output=True,text=True,timeout=10)
assert p.returncode!=0 and 'install Git if missing' in p.stderr,p.stderr
assert snapshot(entry)==before and (store/'current.json').read_bytes()==current
rows.append(dict(case='missing Git integrity check',refused=True,error=p.stderr.strip(),entry_unchanged=True))
"""
   assert needle in s;return s.replace(needle,extra+needle)
  replay('runtime-installed-journey/repair.py',label,'runtime-installed-journey-0064',repair)
else:raise SystemExit('contracts')
