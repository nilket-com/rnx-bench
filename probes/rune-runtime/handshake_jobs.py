"""Diagnostic only: durable job-start before GO, no writes while native clock runs."""
import os,pathlib,select,signal,subprocess,time
from jobs import Jobs
class HandshakeJobs(Jobs):
 def clock(self,argv,label,deadline=30,before_go=None):
  self.serial+=1;prefix=self.out/(f'{self.serial:05d}-'+label)
  self.event('job-request',label=label,argv=list(map(str,argv)),deadline_s=deadline)
  began=time.monotonic();p=subprocess.Popen(list(map(str,argv)),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  self.live[p.pid]=p
  try:
   assert select.select([p.stdout],[],[],deadline)[0], 'READY timeout'
   assert p.stdout.readline()==b'READY\n', 'bad READY'
   self.event('job-start',label=label,pid=p.pid,group=p.pid,start_ticks=pathlib.Path(f'/proc/{p.pid}/stat').read_text().rsplit(') ',1)[1].split()[19])
   if before_go:before_go()
   go=time.monotonic_ns();p.stdin.write(b'G');p.stdin.flush();p.stdin.close();p.stdin=None
   stdout,stderr=p.communicate(timeout=max(.001,deadline-(time.monotonic()-began)))
   reaped=time.monotonic_ns();assert p.returncode==0,(label,p.returncode,stderr)
   fields=stderr.decode().split();assert len(fields)==3 and fields[0]=='STAMP'
   start,end=map(int,fields[1:]);assert go<=start<=end<=reaped
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   del self.live[p.pid]
   pathlib.Path(str(prefix)+'.stdout').write_bytes(stdout);pathlib.Path(str(prefix)+'.stderr').write_bytes(stderr)
   gaps=dict(go_to_start_ns=start-go,end_to_reap_ns=reaped-end,start_ns=start,end_ns=end,go_ns=go,reap_ns=reaped)
   self.event('job-end',label=label,pid=p.pid,status=p.returncode,stdout_file=pathlib.Path(str(prefix)+'.stdout').name,stderr_file=pathlib.Path(str(prefix)+'.stderr').name,**gaps)
   return stdout,gaps
  except BaseException:
   self.cleanup();raise
