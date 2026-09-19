"""Stock self-delegation, same-PID scratch handover, exact shell reopen."""
from pathlib import Path
import os,sys,json,shutil,importlib.util,select,time,subprocess as sp
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/stock-management-0067';D=W/'scratch';D.mkdir(exist_ok=True)
T=D/"stock's rnx";shutil.copy2(W/'rnx',T)
E=json.loads((W/'stock-startup/env.json').read_text());E.update(RNX_DEP_RUNTIME=str(W/'stock-startup/native'),XDG_STATE_HOME=str(D/"state's space"),RNX_PROJECT_CACHE=str(D/'cache'),RNX_HISTORY=str(D/'history'),STARTUP_EVENTS=str(D/'builders'),RNX_PROJECT_TOOL=str(D/'absent-manager'))
# Remove both installed frontends from PATH; keep only build prerequisites.
path=D/'bin';path.mkdir(exist_ok=True)
for n in ['cargo','rustc','rustdoc','git','cc','gcc','ld','as','ar','ranlib']:
 p=shutil.which(n)
 if p:(path/n).symlink_to(p)
E['PATH']=str(path)
spec=importlib.util.spec_from_file_location('term',B/'probes/project-interactive/common.py');term=importlib.util.module_from_spec(spec);spec.loader.exec_module(term)
def until(t,needle):
 out='';end=time.monotonic()+20
 while time.monotonic()<end:
  if select.select([t.master],[],[],.1)[0]:
   b=os.read(t.master,65536);t.log+=b;out+=term.text(b)
   if needle in out:return out
 raise AssertionError((needle,out))
t=term.Terminal([T,'--no-splash','--color=never'],D,E)
try:
 t.read();pid=t.p.pid;t.send('let held=42;');os.write(t.master,b':dep --offline polars\n');notice=until(t,'Continue? [y/N]');assert 'New scratch project:' in notice
 os.write(t.master,b'y\n');out=t.read(timeout=300);assert 'restart is beginning' in out and '[1] >' in out and t.p.pid==pid,out
 assert '73' in t.send('polars::answer()');assert 'error' in t.send('held').lower();assert str(D) in t.send('fs::cwd().unwrap()')
 assert 'already installed; session unchanged' in t.send(':dep polars')
 command=out.split('Reopen this scratch session:\r\n',1)[1].split('\r\n',1)[0].strip();assert "'\\''" in command and ' project session --manifest ' in command,command
 os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
finally:(O/'scratch-handover.pty').write_bytes(t.log);t.close()
# Execute the exact line; neither manager name is on PATH.
p=sp.run(['/bin/sh','-c',command],env=E,cwd=D,input='polars::answer()\n:q\n',capture_output=True,text=True,timeout=30);assert p.returncode==0 and '73' in p.stdout,(p.stdout,p.stderr)
(O/'scratch.json').write_text(json.dumps(dict(same_pid=pid,binding_lost=True,cwd=str(D),manager_on_PATH=False,reopen_command=command,reopened_stdout=p.stdout,builders=(D/'builders').read_text()),indent=2)+'\n');print('PASS stock scratch and exact quoted reopen')
