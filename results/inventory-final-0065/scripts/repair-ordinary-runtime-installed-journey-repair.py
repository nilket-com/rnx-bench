"""F3: product status-induced drift repair only after source/object validation."""
from pathlib import Path
import os,subprocess as sp,shutil,json,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=Path('/home/me/work/rnx-bench/probes/inventory-final/target/repair-ordinary');O=B/'results/inventory-final-0065/repair-ordinary';T=Path(os.environ.get('RNX_REPAIR_TOOL',R/'tools/project/target/release/rnx-project'))
assert not W.exists();W.mkdir();O.mkdir(exist_ok=True)
E={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','GIT_'))};E.update(XDG_DATA_HOME=str(W/'data'),RNX_PROJECT_CACHE=str(W/'cache'),XDG_STATE_HOME=str(W/'state'))
def run(args,ok=True):
 p=sp.run(list(map(str,args)),env=E,capture_output=True,text=True,timeout=30);assert (p.returncode==0)==ok,(args,p.stdout,p.stderr);return p
src=W/'source';(src/'src').mkdir(parents=True);(src/'Cargo.toml').write_text('[package]\nname="rnx"\nversion="0.0.0"\nedition="2024"\n[workspace]\n');(src/'src/lib.rs').write_text('// source\n');(src/'src/main.rs').write_text('fn main() {}\n')
for a in ['polars','postgres']:
 p=src/'adapters'/a;(p/'src').mkdir(parents=True);(p/'src/lib.rs').write_text('// adapter\n');(p/'Cargo.toml').write_text(f'[package]\nname="rnx-{a}"\nversion="0.0.0"\n[workspace]\n[dependencies]\nrnx={{path="../.."}}\n')
run(['git','init','-q',src]);run(['git','-C',src,'add','.'])
id=run([T,'runtime','install','--from',src]).stdout.split('runtime ',1)[1].splitlines()[0];store=W/'data/rnx/runtimes';entry=store/'entries'/id;source=entry/'source';index=source/'.git/index';doc=(entry/'installation.json').read_bytes();current=(store/'current.json').read_bytes();rows=[]
def snapshot(root):return {str(p.relative_to(root)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mode,p.stat().st_ino,p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
def status():
 # Touch stat information so ordinary Git really refreshes/replaces the index.
 os.utime(source/'src/lib.rs',None)
 p=sp.run(['git','-C',str(source),'status','--porcelain'],env=E,umask=0o002,capture_output=True,text=True);assert p.returncode==0,p.stderr
 assert index.stat().st_mode&0o777==0o664,oct(index.stat().st_mode)
 return snapshot(entry)
for command in [[T,'runtime','install','--from',src],[T,'runtime','select',id]]:
 before=status();result=run(command);after=snapshot(entry)
 assert index.stat().st_mode&0o777==0o600
 assert before.keys()==after.keys()
 assert all(before[k][0]==after[k][0] and before[k][2:]==after[k][2:] for k in before)
 assert (entry/'installation.json').read_bytes()==doc
 rows.append(dict(case='status drift '+command[2],index_before='0664',index_after='0600',bytes_inode_mtime_unchanged=True))
# Poison an object while source bytes remain correct; neither writer may chmod it.
for what in ['blob','source']:
 for command in [[T,'runtime','install','--from',src],[T,'runtime','select',id]]:
  status();path=next(p for p in (source/'.git/objects').glob('*/*') if p.is_file()) if what=='blob' else source/'src/lib.rs'
  original=path.read_bytes();mode=path.stat().st_mode;path.chmod(0o600);path.write_bytes(b'corrupted object or source');before=snapshot(entry);r=run(command,ok=False)
  if what=='blob':assert 'corrupt installed runtime' in r.stderr and 'install Git if missing' not in r.stderr,r.stderr
  assert snapshot(entry)==before;assert (store/'current.json').read_bytes()==current
  rows.append(dict(case=what+' corruption '+command[2],refused=True,no_permission_or_content_write=True,error=r.stderr.strip()))
  path.write_bytes(original);path.chmod(mode&0o777);run([T,'runtime','select',id])
# Source mode drift does not expand the Git-only exception.
path=source/'src/lib.rs';path.chmod(0o664);before=snapshot(entry);run([T,'runtime','select',id],ok=False);assert snapshot(entry)==before;path.chmod(0o600)
rows.append(dict(case='source permissions stay strict',refused=True))
# Missing Git still gets prerequisite guidance and changes no state.
empty=W/'empty-path';empty.mkdir();before=snapshot(entry)
p=sp.run([str(T),'runtime','select',id],env=dict(E,PATH=str(empty)),capture_output=True,text=True,timeout=10)
assert p.returncode!=0 and 'install Git if missing' in p.stderr,p.stderr
assert snapshot(entry)==before and (store/'current.json').read_bytes()==current
rows.append(dict(case='missing Git integrity check',refused=True,error=p.stderr.strip(),entry_unchanged=True))
(O/os.environ.get('RNX_REPAIR_RESULT','repair.json')).write_text(json.dumps(rows,indent=2)+'\n');print('PASS',len(rows),'repair cases')
