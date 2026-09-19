"""Wall time, counted data and free-space deltas are separate observations."""
from pathlib import Path
import os,json,subprocess as sp,shutil,time,selectors,signal,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target/costs';O=B/'results/removal-final-0066/costs';assert not W.exists();W.mkdir();O.mkdir(exist_ok=True);os.umask(0o077)
T=H/'target/tool-ordinary';S=H/'target/tool-support';setup=json.loads((B/'probes/removal-storage/target/real/setup.json').read_text());journey=json.loads((B/'results/removal-storage-0066/journey.json').read_text());original=Path(setup['store']);selection=(original/'current.json').read_bytes();runtime_id=json.loads(selection)['id']
polars=Path(journey['default_journeys']['first_scratch']['artifact']).parent.parent
combined=polars.parent/journey['current_build']['key']
E={k:v for k,v in os.environ.items() if not k.startswith('RNX_REMOVE_')};rows=[]
def free(p):s=os.statvfs(p);return s.f_bavail*s.f_frsize
def call(a):
 start=time.perf_counter_ns();p=sp.run(list(map(str,a)),env=E,capture_output=True,text=True,timeout=120);elapsed=(time.perf_counter_ns()-start)/1e6;assert p.returncode==0,(a,p.stdout,p.stderr);return p,elapsed
def stats(path):
 files=[]
 for base,ds,fs in os.walk(path):
  for n in ds+fs:
   p=Path(base)/n;s=p.lstat();files.append((str(p.relative_to(path)),s.st_ino,s.st_mtime_ns,s.st_mode,s.st_size))
 return files
# Whole-directory copies are never executed; their old absolute references do not
# authorize deleting the originals. No reflink is requested and no synthetic padding is used.
for label,source,kind,interrupted in [('polars',polars,'cache',False),('combined',combined,'cache',True),('runtime',original/'entries'/runtime_id,'runtime',False)]:
 root=W/label;entries=root/'entries';entries.mkdir(parents=True);key=source.name;dest=entries/key
 before=stats(source);os.sync();before_copy=free(root);shutil.copytree(source,dest,symlinks=True)
 if kind=='cache':(root/'locks').mkdir();lock=root/'locks'/f'{key}.lock';lock.touch()
 else:lock=root/'install.lock';lock.touch()
 inode=lock.stat().st_ino;os.sync();after_copy=free(root)
 p,list_ms=call([T,kind,'list','--root',root]);listing=json.loads(p.stdout);(O/(label+'-list.json')).write_text(p.stdout)
 p,dry_ms=call([T,kind,'remove',key,'--root',root,'--dry-run']);dry=json.loads(p.stdout);(O/(label+'-dry.json')).write_text(p.stdout)
 assert dry['entries'][0]['nodes']==1+len(stats(dest)),dry
 metrics=dict(label=label,kind=kind,source=str(source),list_ms=list_ms,dry_ms=dry_ms,nodes=dry['entries'][0]['nodes'],files=dry['entries'][0]['files'],logical_bytes=dry['entries'][0]['logical'],allocated_estimate=dry['entries'][0]['allocated_estimate'],free_before_copy=before_copy,free_after_copy=after_copy,copy_free_delta=before_copy-after_copy)
 if interrupted:
  start=time.perf_counter_ns();child=sp.Popen(list(map(str,[S,kind,'remove',key,'--root',root,'--quiescent'])),env=dict(E,RNX_REMOVE_PAUSE='during-delete',RNX_REMOVE_RELEASE=str(root/'release')),stdout=sp.PIPE,stderr=sp.PIPE);sel=selectors.DefaultSelector();sel.register(child.stdout,selectors.EVENT_READ);buf=b'';events=[];ready=False
  try:
   end=time.monotonic()+30
   while time.monotonic()<end and not ready:
    if not sel.select(.1):assert child.poll() is None;continue
    chunk=os.read(child.stdout.fileno(),65536);assert chunk;buf+=chunk
    while b'\n' in buf:
     line,buf=buf.split(b'\n',1);v=json.loads(line);events.append(v)
     if v.get('paused')=='during-delete':ready=True
   assert ready;metrics['spawn_to_pause_ms']=(time.perf_counter_ns()-start)/1e6
   child.kill();child.communicate(timeout=10);assert child.returncode==-signal.SIGKILL
  finally:
   if child.poll() is None:child.kill()
   child.wait(timeout=10);sel.close()
  assert not dest.exists();os.sync();before_resume=free(root)
  p,pending_ms=call([T,kind,'remove',key,'--root',root,'--resume','--dry-run']);(O/(label+'-pending.json')).write_text(p.stdout)
  pending=json.loads(p.stdout)['entries'][0];p,remove_ms=call([T,kind,'remove',key,'--root',root,'--resume','--quiescent']);metrics.update(resume_ms=remove_ms,pending_dry_ms=pending_ms,pending_nodes=pending['nodes'],pending_logical=pending['logical'],free_before_resume=before_resume,pause_events=events)
 else:
  os.sync();before_resume=free(root);p,remove_ms=call([T,kind,'remove',key,'--root',root,'--quiescent']);metrics.update(remove_ms=remove_ms,free_before_remove=before_resume)
 os.sync();after=free(root);metrics.update(free_after_remove=after,observed_free_increase=after-before_resume,report=[json.loads(x) for x in p.stdout.splitlines()])
 assert not dest.exists() and not (root/'removing'/key).exists() and lock.stat().st_ino==inode and stats(source)==before
 metrics['original_metadata_unchanged']=True;metrics['lock_inode_retained']=True;rows.append(metrics);print(label,{k:v for k,v in metrics.items() if k in ['nodes','logical_bytes','allocated_estimate','list_ms','dry_ms','remove_ms','resume_ms','observed_free_increase']},flush=True)
assert (original/'current.json').read_bytes()==selection
(O/'measurements.json').write_text(json.dumps(rows,indent=2)+'\n')
(O/'conditions.json').write_text(json.dumps(dict(sync='os.sync before/after free-space readings; excluded from command wall times',filesystem='shared host filesystem; unrelated allocation can affect statvfs deltas',copy='whole-directory copies, never executed, no synthetic padding or explicit reflink request',samples_per_operation=1,cache='warmed by copy; no cold-cache claim',free='f_bavail * f_frsize',scope='single-host observations, no exact reclamation promise',original_selection_unchanged=True),indent=2)+'\n')
