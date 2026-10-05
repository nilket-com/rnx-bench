"""Bounded commands, owned process groups and durable admission/job ledger."""
import ctypes, json, os, pathlib, signal, subprocess, time
LOCK='/tmp/rnx-runtime-bench.lock'
# Reap adopted descendants after killing an owned command group (Linux worker).
assert ctypes.CDLL(None,use_errno=True).prctl(36,1,0,0,0)==0
class Jobs:
 def __init__(self,out):
  self.out=pathlib.Path(out);self.live={};self.serial=0
  self.out.mkdir(parents=True,exist_ok=True)
 def event(self,kind,**data):
  with (self.out/'ledger.jsonl').open('a') as f:f.write(json.dumps(dict(kind=kind,monotonic_ns=time.monotonic_ns(),utc=time.time(),**data))+'\n');f.flush();os.fsync(f.fileno())
 def cleanup(self):
  for pid,p in list(self.live.items()):
   try:os.killpg(pid,signal.SIGKILL)
   except ProcessLookupError:pass
   try:p.wait(timeout=5)
   except subprocess.TimeoutExpired:raise RuntimeError('cannot reap owned command '+str(pid))
   del self.live[pid]
  end=time.monotonic()+5
  while True:
   try:pid,status=os.waitpid(-1,os.WNOHANG)
   except ChildProcessError:break
   if pid:continue
   if time.monotonic()>end:raise RuntimeError('owned descendants still live after cleanup')
   time.sleep(.01)
 def run(self,argv,label,deadline=30,expected=None,env=None,cwd=None,allowed=(0,),limits=None):
  self.serial+=1;prefix=self.out/(f'{self.serial:05d}-'+label)
  self.event('job-request',label=label,argv=list(map(str,argv)),deadline_s=deadline)
  with pathlib.Path(str(prefix)+'.stdout').open('wb') as so,pathlib.Path(str(prefix)+'.stderr').open('wb') as se:
   def bounded():
    if limits:
     import resource
     resource.setrlimit(resource.RLIMIT_CORE,(0,0))
     resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
     resource.setrlimit(resource.RLIMIT_CPU,(5,6))
   p=subprocess.Popen(list(map(str,argv)),stdout=so,stderr=se,stdin=subprocess.DEVNULL,start_new_session=True,env=env,cwd=cwd,preexec_fn=bounded if limits else None)
   self.live[p.pid]=p;self.event('job-start',label=label,pid=p.pid,group=p.pid,start_ticks=pathlib.Path(f'/proc/{p.pid}/stat').read_text().rsplit(') ',1)[1].split()[19])
   try:status=p.wait(timeout=deadline)
   except subprocess.TimeoutExpired:
    self.event('job-timeout',label=label,pid=p.pid);self.cleanup();raise RuntimeError(label+': timeout')
   # A normally exited parent is not allowed to leave a group behind.
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   del self.live[p.pid]
  stdout=pathlib.Path(str(prefix)+'.stdout').read_bytes();stderr=pathlib.Path(str(prefix)+'.stderr').read_bytes()
  self.event('job-end',label=label,pid=p.pid,status=status,stdout_file=pathlib.Path(str(prefix)+'.stdout').name,stderr_file=pathlib.Path(str(prefix)+'.stderr').name)
  if status not in allowed:raise RuntimeError(f'{label}: status {status}; '+stderr[-2000:].decode(errors='replace'))
  if expected is not None and (stdout!=expected or stderr):raise RuntimeError(label+': output mismatch')
  return status,stdout,stderr
 def locked(self,phase,worker,timeout_s):
  self.event('lock-request',phase=phase,lock=LOCK)
  # Worker emits acquisition; its timeout starts after flock admission.
  return self.run(['flock','--exclusive','--timeout','1800',LOCK,'timeout','--kill-after=5s',str(timeout_s)+'s',*worker],phase,deadline=1800+timeout_s+10)

def stop_registered(ledger):
 """Supervisor fallback if a worker was killed before its own finally ran."""
 ledger=pathlib.Path(ledger)
 if not ledger.exists():return
 live={}
 for line in ledger.read_text().splitlines():
  r=json.loads(line)
  if r['kind']=='job-start':live[r['pid']]=r
  elif r['kind']=='job-end':live.pop(r['pid'],None)
 for pid,r in live.items():
  stat=pathlib.Path(f'/proc/{pid}/stat')
  if stat.exists() and stat.read_text().rsplit(') ',1)[1].split()[19]!=r['start_ticks']:continue
  try:os.killpg(pid,signal.SIGKILL)
  except ProcessLookupError:pass
