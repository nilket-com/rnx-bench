from common import *
import importlib.util,select,shlex,shutil,sys
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('term',B/'probes/project-interactive/common.py');term=importlib.util.module_from_spec(spec);spec.loader.exec_module(term)
setup=json.loads((O/'real-setup.json').read_text());exe=Path(setup['exe']);D=T/'real-journey';D.mkdir(exist_ok=True)
E=ENV|{'TERM':'xterm-256color','RNX_HISTORY':str(D/'history'),'RNX_CONFIG':str(D/'absent-config')}
def until(t,needle):
 out='';end=time.monotonic()+30
 while time.monotonic()<end:
  if select.select([t.master],[],[],.1)[0]:
   b=os.read(t.master,65536);t.log+=b;out+=term.text(b)
   if needle in out:return out
 raise AssertionError((needle,out))
rows=[]
for n in [1,2]:
 env=E.copy()
 if n==2:
  traps=D/'traps';traps.mkdir(exist_ok=True);
  for name in ['cargo','rustc']:
   actual=shutil.which(name,path=E['PATH']);f=traps/name
   if name=='cargo':body='case "$1" in build) echo compilation-trapped >&2; exit 98;; esac\n'
   else:body='case "$1" in -V|-Vv|-vV) ;; *) case " $* " in *--print*) ;; *) echo compiler-trapped >&2; exit 98;; esac;; esac\n'
   f.write_text('#!/bin/sh\n'+body+'exec '+shlex.quote(actual)+' "$@"\n');f.chmod(0o700)
  env['PATH']=str(traps)+':'+E['PATH']
 args=['taskset','-c','0-3',exe,'--no-splash','--color=never']
 if n==2:
  # Positive controls for compiler traps, then block networking at the namespace.
  assert run(['cargo','build'],env=env,ok=False).returncode==98
  assert run(['rustc','input.rs'],env=env,ok=False).returncode==98
  args=['bwrap','--unshare-user','--uid',str(os.getuid()),'--gid',str(os.getgid()),'--unshare-net','--bind','/','/','--dev','/dev','--proc','/proc','--',*args]
 t=term.Terminal(args,D,env)
 try:
  t.read();pid=t.p.pid
  if n==2:
   todo=[pid];matches=[]
   while todo:
    candidate=todo.pop()
    try:
     if Path('/proc',str(candidate),'exe').resolve()==exe.resolve():matches.append(candidate)
     todo += list(map(int,Path('/proc',str(candidate),'task',str(candidate),'children').read_text().split()))
    except FileNotFoundError:pass
   assert len(matches)==1,matches
   pid=matches[0]
  t.send('let held=42;');os.write(t.master,(':dep '+('--offline ' if n==2 else '')+'polars\n').encode());notice=until(t,'Continue? [y/N]');assert 'acquired' in notice and setup['rev'] in notice,notice
  start=time.monotonic();os.write(t.master,b'y\n');out=t.read(timeout=1500);elapsed=time.monotonic()-start
  assert 'restart is beginning' in out and '[1] >' in out and Path('/proc',str(pid)).exists(),out
  (D/f'data{n}.csv').write_text('category,value\na,1\na,2\nb,3\n')
  out=t.send(f'let frame=polars::read_csv("data{n}.csv",[("category","string"),("value","i64")]).unwrap();');assert 'error:' not in out,out
  preview=t.send('frame.preview().unwrap()');assert '3 rows' in preview or '3 × 2' in preview or '3 x 2' in preview,preview
  assert 'error' in t.send('held').lower();assert str(D) in t.send('fs::cwd().unwrap()');assert 'already installed; session unchanged' in t.send(':dep polars')
  log=term.text(t.log);command=log.split('Reopen this scratch session:\r\n',1)[1].split('\r\n',1)[0].strip();manifest=Path(shlex.split(command)[-1]);lock=json.loads((manifest.parent/'rnx.lock').read_text());assert lock['format']==4 and lock['declarations']['runtime']['rev']==setup['rev'];assert all(g['revision']==setup['rev'] for g in lock['git'])
  os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
  rows.append({'consumer':n,'seconds':elapsed,'same_pid':pid,'manifest':str(manifest),'identity':lock['assembly']['identity'],'reopen':command,'preview':preview,'compilation_trapped':n==2,'network_namespace_disabled':n==2})
 finally:(O/f'real-journey-{n}.pty').write_bytes(t.log);t.close()
 assert rows[0]['identity']==rows[-1]['identity']
 save('real-journeys-progress.json',rows)
save('real-journeys.json',rows);print('Two acquired Git Polars journeys pass',flush=True)
