"""Actual fresh processes, closed ordered receipts, bounded descendant cleanup."""
import json,os,pathlib,signal,sys,time
from resident import run_plan,parse
P=pathlib.Path(__file__).resolve().parent
def controls(j,out):
 cmd=[sys.executable,'-c','import os;print(os.getpid())']
 rows=run_plan(j,out,[cmd]*6,'control-fresh-pids')
 pids=[int(r['stdout']) for r in rows];assert len(set(pids))==6 and all(r['status']==0 and not r['stderr'] for r in rows)
 receipt=json.loads((out/'plans/control-fresh-pids.json').read_text());payload=(out/receipt['native_raw']).read_bytes();parse(payload,[cmd]*6)
 lines=payload.decode().splitlines();refused=[]
 for name,bad in [('missing',lines[:-6]),('extra',lines+lines[-6:]),('reordered',lines[6:12]+lines[:6]+lines[12:])]:
  try:parse(('\n'.join(bad)+'\n').encode(),[cmd]*6)
  except AssertionError:refused.append(name)
  else:raise RuntimeError('accepted '+name)
 marker=out/'resident-descendant.pid'
 child=[sys.executable,'-c',f'import subprocess,time,pathlib; p=subprocess.Popen(["sleep","30"]);pathlib.Path({str(marker)!r}).write_text(str(p.pid));time.sleep(30)']
 try:run_plan(j,out,[child],'control-timeout-descendant',deadline=.3)
 except RuntimeError as e:assert 'timeout' in str(e)
 else:raise RuntimeError('timeout control did not expire')
 assert marker.exists();pid=int(marker.read_text());assert not pathlib.Path('/proc/'+str(pid)).exists(),'descendant not reaped'
 (out/'resident-controls.json').write_text(json.dumps(dict(fresh_pids=pids,refused=refused,timeout_descendant='killed-and-reaped',plan_integrity='declared/executed hashes equal'),indent=2)+'\n')
