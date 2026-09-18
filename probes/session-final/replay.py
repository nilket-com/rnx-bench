"""Replay accepted fixtures, archive fresh results, restore their published results."""
from pathlib import Path
import os,sys,subprocess,shutil,tempfile,json,time
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/session-final-0063/replay';O.mkdir(parents=True,exist_ok=True)
# The caller builds root default and tool test-support debug binaries first.
rows=[]
def replay(name,commands,result,target=None):
 original=B/'results'/result
 with tempfile.TemporaryDirectory(prefix='rnx-0063-replay-') as tmp:
  backup=Path(tmp)/'results'
  if original.exists():
   shutil.copytree(original,backup);shutil.rmtree(original);original.mkdir()
  if target and (B/target).exists():
   old=B/(target+'-pre-final');assert not old.exists(),old;(B/target).rename(old)
  start=time.monotonic()
  try:
   for i,cmd in enumerate(commands):
    with (O/f'{name}-{i}.log').open('w') as f:p=subprocess.run(cmd,cwd=B,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
    assert p.returncode==0,(name,i)
   shutil.copytree(original,O/name)
   rows.append({'name':name,'seconds':time.monotonic()-start,'commands':commands,'passed':True})
  finally:
   if original.exists():shutil.rmtree(original)
   if backup.exists():shutil.copytree(backup,original)
 (O/'checks.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS',name,flush=True)
replay('preparation',[[sys.executable,'probes/session-preparation/setup.py'],[sys.executable,'probes/session-preparation/check.py']],'session-preparation-0063','probes/session-preparation/target')
replay('startup',[[sys.executable,'probes/session-startup/setup.py'],[sys.executable,'probes/session-startup/check.py']],'session-startup-0063','probes/session-startup/target')
subprocess.run([sys.executable,'probes/session-final/cache.py'],cwd=B,check=True)
