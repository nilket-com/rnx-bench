import os,pathlib,subprocess,pty,fcntl,termios,struct,select,time,re,errno,signal
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/project-interactive-0060';P=H/'target/project';T=R/'tools/project/target/release/rnx-project'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_','POLARS_'))}
ENV.update(TERM='xterm-256color',POLARS_MAX_THREADS='1',RNX_CONFIG=str(H/'target/absent-config'),RNX_HISTORY=str(H/'target/history'),PYTHONDONTWRITEBYTECODE='1')
ANSI=re.compile(rb'\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)')
def text(b):return ANSI.sub(b'',b).decode('utf8',errors='replace')
def controlling():
 os.setsid();fcntl.ioctl(0,termios.TIOCSCTTY,0)
class Terminal:
 def __init__(self,argv,cwd,env=ENV):
  self.master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,120,0,0));self.log=b''
  try:self.p=subprocess.Popen(list(map(str,argv)),stdin=slave,stdout=slave,stderr=slave,cwd=cwd,env=env,preexec_fn=controlling)
  except BaseException:os.close(self.master);raise
  finally:os.close(slave)
 def read(self,until=True,timeout=15):
  out=b'';end=time.monotonic()+timeout
  while time.monotonic()<end:
   if select.select([self.master],[],[],.1)[0]:
    try:b=os.read(self.master,65536)
    except OSError as e:
     if e.errno==errno.EIO:break
     raise
    if not b:break
    out+=b;self.log+=b
    if until and re.search(r'\[\d+\] > \r*$',text(out)):return text(out)
   elif self.p.poll() is not None:break
  if until:raise AssertionError(('no prompt',self.p.poll(),text(out)))
  return text(out)
 def send(self,line):os.write(self.master,line.encode()+b'\n');return self.read()
 def close(self):
  if self.p.poll() is None:self.p.kill()
  self.p.wait(timeout=5);os.close(self.master)
def call(argv,cwd=None,stdin=None,env=ENV):return subprocess.run(list(map(str,argv)),cwd=cwd,env=env,input=stdin,capture_output=True,text=True,timeout=60)
