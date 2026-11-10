"""Genuine installation-1 authentication and migration under real writer paths."""
from pathlib import Path
import os,subprocess as sp,json,shutil,hashlib,signal,time,shlex
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=Path('/home/me/work/rnx-bench/probes/git-source-workflow/target/storage-migration/matrix');O=Path('/home/me/work/rnx-bench/results/git-source-workflow-0067/storage-migration');assert not W.exists();W.mkdir(parents=True);O.mkdir(exist_ok=True)
OLD=Path('/home/me/work/rnx-bench/probes/git-source-workflow/target/storage-migration/old/tools/project/target/debug/rnx-project');T=Path('/home/me/work/rnx-bench/probes/git-source-workflow/target/rnx-project');E={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','GIT_','CARGO_','RUST'))};E.update(XDG_DATA_HOME=str(W/"data space'quote"),RNX_PROJECT_CACHE=str(W/'cache'));store=Path(E['XDG_DATA_HOME'])/'rnx/runtimes';rows=[]
def call(args,env=E,ok=True,tool=T):
 p=sp.run([str(tool),'runtime',*map(str,args)],env=env,capture_output=True,text=True,timeout=45);assert (p.returncode==0)==ok,(args,p.returncode,p.stdout,p.stderr);return p
s=W/'original';(s/'src').mkdir(parents=True);(s/'Cargo.toml').write_text('[package]\nname="rnx"\nversion="0.0.0"\nedition="2024"\n[workspace]\n');(s/'src/main.rs').write_text('fn main() {}\n');(s/'src/lib.rs').write_text('// runtime\n')
for a in ['polars','postgres']:
 d=s/'adapters'/a;(d/'src').mkdir(parents=True);(d/'src/lib.rs').write_text('// adapter\n');(d/'Cargo.toml').write_text(f'[package]\nname="rnx-{a}"\nversion="0.0.0"\n[workspace]\n[dependencies]\nrnx={{path="../.."}}\n')
for args in [['init','-q'],['add','.'],['-c','user.name=Fixture','-c','user.email=f@invalid','-c','commit.gpgsign=false','commit','-qm','snapshot']]:sp.run(['git','-C',s,*args],env=E,check=True)
id=call(['install','--from',s],tool=OLD).stdout.split('runtime ',1)[1].splitlines()[0];entry=store/'entries'/id;old_doc=json.loads((entry/'installation.json').read_text());assert old_doc['format']==1;s.rename(W/'unavailable-checkout')
def snap(p):return {str(f.relative_to(p)):(hashlib.sha256(f.read_bytes()).hexdigest(),f.stat().st_mtime_ns,f.stat().st_ino,f.stat().st_mode) for f in p.rglob('*') if f.is_file()}
def record(name,**kw):rows.append(dict(name=name,**kw));(O/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS',name,flush=True)
original=snap(entry);selection=(store/'current.json').read_bytes()
for args in [['show'],['select',id]]:
 p=call(args,ok=False);line=next(l for l in p.stderr.splitlines() if ' runtime install --from ' in l)
 assert shlex.split(line)==[str(T),'runtime','install','--from',str(entry/'source')];assert snap(entry)==original and (store/'current.json').read_bytes()==selection
record('old discovery and select refuse with exact quoted recovery, unchanged old payloads')
# Clones retain the original schema/objects/index, never synthesized old documents.
def case(name):
 data=W/name;st=data/'rnx/runtimes';shutil.copytree(store,st);return dict(E,XDG_DATA_HOME=str(data)),st,st/'entries'/id
for label in ['source','blob','metadata','id','mixed','unknown']:
 env,st,en=case('corrupt-'+label);src=en/'source';idx=src/'.git/index';idx.chmod(0o664)
 if label=='source':p=src/'src/lib.rs';p.write_bytes(p.read_bytes()+b'x')
 elif label=='blob':p=next(p for p in (src/'.git/objects').glob('*/*') if p.is_file());p.chmod(0o600);blob=p.read_bytes();p.write_bytes(blob[:-1]+bytes([blob[-1]^1]));p.chmod(0o400)
 else:
  p=en/'installation.json';d=json.loads(p.read_text());d.update({'metadata':{'tree_sha256':'0'*64},'id':{'id':'0'*64},'mixed':{'tree_blake3':'0'*64},'unknown':{'format':99}}[label]);p.write_text(json.dumps(d))
 before=snap(en);raw=(st/'current.json').read_bytes();r=call(['install','--from',src],env,False);assert snap(en)==before and (st/'current.json').read_bytes()==raw and len(list((st/'entries').iterdir()))==1;assert idx.stat().st_mode&0o777==0o664
 record('authentication refuses '+label,error=r.stderr.strip())
pre=['after-snapshot','copy-chunk','after-copy','git-step','after-index','before-document','after-document','before-entry-rename'];post=['after-entry-rename','after-entry-sync','before-current-write','after-current-write','before-current-rename'];late=['after-current-rename','after-current-sync']
for point in pre+post+late:
 env,st,en=case('failure-'+point);before=snap(en);r=call(['install','--from',en/'source'],dict(env,RNX_INSTALL_FAIL=point),False);assert snap(en)==before
 assert len(list((st/'entries').iterdir()))==(1 if point in pre else 2)
 if point in late:assert 'selection may already have changed' in r.stderr
 else:assert (st/'current.json').read_bytes()==selection
 if point in post:assert 'installed but not selected' in r.stderr
 assert not list(st.glob('.stage-*')) and not list(st.glob('.current-*'))
 record('migration publication '+point)
for point in ['copy-chunk','git-step']:
 for sig in [signal.SIGINT,signal.SIGTERM]:
  env,st,en=case(f'interrupt-{point}-{sig}');marker=W/f'pause-{point}-{sig}';before=snap(en)
  p=sp.Popen([T,'runtime','install','--from',en/'source'],env=dict(env,RNX_INSTALL_PAUSE=point,RNX_INSTALL_MARKER=str(marker)),stdout=sp.PIPE,stderr=sp.PIPE)
  try:
   end=time.monotonic()+20
   while not marker.exists():assert p.poll() is None and time.monotonic()<end;time.sleep(.01)
   p.send_signal(sig);p.communicate(timeout=10);assert p.returncode==128+sig
  finally:
   if p.poll() is None:p.kill();p.communicate()
   marker.unlink(missing_ok=True)
  assert snap(en)==before and (st/'current.json').read_bytes()==selection and len(list((st/'entries').iterdir()))==1 and not list(st.glob('.stage-*'))
  record(f'migration interruption {point} {sig.name}')
# Reauthenticate after the final staging pause; never publish from changed old state.
for label in ['source','provenance']:
 env,st,en=case('late-edit-'+label);marker=W/('late-'+label);p=sp.Popen([T,'runtime','install','--from',en/'source'],env=dict(env,RNX_INSTALL_PAUSE='before-entry-rename',RNX_INSTALL_MARKER=str(marker)),stdout=sp.PIPE,stderr=sp.PIPE)
 try:
  end=time.monotonic()+20
  while not marker.exists():assert p.poll() is None and time.monotonic()<end;time.sleep(.01)
  if label=='source':q=en/'source/src/lib.rs';q.write_bytes(q.read_bytes()+b'x')
  else:
   q=en/'installation.json';doc=json.loads(q.read_text());doc['source_path']='/different/provenance';q.write_text(json.dumps(doc))
  changed=snap(en);marker.with_suffix(".release").touch();out,err=p.communicate(timeout=20);assert p.returncode!=0 and not out,(out,err)
  assert snap(en)==changed and len(list((st/'entries').iterdir()))==1 and (st/'current.json').read_bytes()==selection
 finally:
  if p.poll() is None:p.kill();p.communicate()
  marker.unlink(missing_ok=True)
 record('late '+label+' change refuses before publication')
for suffix in ['src','adapters/polars']:
 before=snap(entry);call(['install','--from',entry/'source'/suffix],ok=False);assert snap(entry)==before
record('only exact owned retained source qualifies')
# Successful migration repairs only validated Git administration.
idx=entry/'source/.git/index';idx.chmod(0o664);oldbytes=(entry/'installation.json').read_bytes();r=call(['install','--from',entry/'source']);newid=r.stdout.split('runtime ',1)[1].splitlines()[0];assert newid!=id;new=store/'entries'/newid;d=json.loads((new/'installation.json').read_text());assert d['format']==2 and d['migrated_from']==dict(format=1,id=id)
for field in ['source_path','source_commit','dirty_tracked']:assert d[field]==old_doc[field]
assert (entry/'installation.json').read_bytes()==oldbytes and idx.stat().st_mode&0o777==0o600
assert {k:v[:3] for k,v in snap(entry).items()}=={k:v[:3] for k,v in original.items()}
assert json.loads((store/'current.json').read_text())==dict(format=2,id=newid)
saved=snap(new);call(['install','--from',entry/'source']);assert snap(new)==saved;call(['install','--from',new/'source']);assert snap(new)==saved
record('authenticated migration preserves old provenance, repairs administration, publishes new ID and reselects without rewrite',old=id,new=newid)
(O/'old-installation.json').write_bytes(oldbytes);(O/'new-installation.json').write_bytes((new/'installation.json').read_bytes());(O/'tools.json').write_text(json.dumps({name:dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for name,p in [('old',OLD),('current',T)]},indent=2)+'\n')
