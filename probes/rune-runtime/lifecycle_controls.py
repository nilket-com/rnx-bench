"""Use actual job/lock path; an execution deadline starts only after admission."""
import json,os,pathlib,subprocess,sys,tempfile,time,signal
from jobs import Jobs,LOCK
with tempfile.TemporaryDirectory(prefix='rune-runtime-controls-') as d:
 p=pathlib.Path(d);j=Jobs(p/'jobs')
 # Explicit release file avoids inherited-descriptor close ambiguity.
 holder=subprocess.Popen(['flock','--exclusive','--timeout','1800',LOCK,sys.executable,'-c',
  'import pathlib,time,sys;p=pathlib.Path(sys.argv[1]);p.write_text("ready");\nwhile not p.with_name("release").exists():time.sleep(.01)',str(p/'ready')],start_new_session=True)
 try:
  end=time.monotonic()+1810
  while not (p/'ready').exists():
   assert holder.poll() is None and time.monotonic()<end;time.sleep(.01)
  child=subprocess.Popen(['flock','--exclusive','--timeout','1800',LOCK,'timeout','--kill-after=1s','0.2s',sys.executable,'-c','import pathlib,sys;pathlib.Path(sys.argv[1]).write_text("ran")',str(p/'ran')],start_new_session=True)
  time.sleep(.5);assert child.poll() is None and not (p/'ran').exists()
  (p/'release').write_text('release');holder.wait(timeout=5);assert child.wait(timeout=5)==0 and (p/'ran').read_text()=='ran'
 finally:
  for proc in (holder,locals().get('child')):
   if proc is not None and proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
 # Child leaves a descendant in its owned group; deadline must kill/reap both.
 code='import subprocess,sys,time,pathlib;p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"]);pathlib.Path(sys.argv[1]).write_text(str(p.pid));time.sleep(60)'
 try:j.run([sys.executable,'-c',code,str(p/'pid')],'timeout-descendant',deadline=.3)
 except RuntimeError as e:assert 'timeout-descendant: timeout' in str(e)
 else:raise AssertionError('timeout accepted')
 pid=int((p/'pid').read_text());assert not pathlib.Path('/proc/'+str(pid)).exists()
 j.cleanup()
 print('PASS: held-lock admission, post-admission deadline, timeout kills and reaps descendant')
