from common import *
import select,re,shlex
setup,E=environment('published');exe=Path(setup['exe']);D=T/'published';OUT=O/'selection';OUT.mkdir();cwd=D/'selection-caller';cwd.mkdir();term=load('selection_terminal',B/'probes/project-interactive/common.py')
assert not Path(E['XDG_DATA_HOME']).exists()
source=T/'fixture-checkout-unavailable'
p=run([exe,'runtime','install','--from',source],env=E);(OUT/'install.log').write_bytes(p.stdout+p.stderr)
store=Path(E['XDG_DATA_HOME'])/'rnx/runtimes';current=store/'current.json';original=current.read_bytes();selection=json.loads(original);installed=store/'entries'/selection['id']/'source';assert installed.is_dir()
selection['id']='0'*64;current.write_text(json.dumps(selection));stale=current.read_bytes()
p=run([exe,'runtime','show'],env=E,ok=False);assert p.returncode and b'missing' in p.stderr;(OUT/'stale-refusal.log').write_bytes(p.stdout+p.stderr)
log=D/'selection-compiles.jsonl';log.write_text('');trapped=E|{'PATH':str(D/'traps')+':'+E['PATH'],'ONE_INSTALL_COMPILE_LOG':str(log),'ONE_INSTALL_FORBID_COMPILE':'1'}
def dep(t):
 os.write(t.master,b':dep --offline polars\n');notice='';end=time.monotonic()+30
 while time.monotonic()<end:
  if select.select([t.master],[],[],.1)[0]:
   b=os.read(t.master,65536);t.log+=b;notice+=term.text(b)
   if 'Continue? [y/N]' in notice:break
 else:raise AssertionError(notice)
 os.write(t.master,b'y\n');out=t.read(timeout=1800);assert 'restart is beginning' in out and '[1] >' in out,out
 assert 'true' in t.send('polars::lit(1).is_ok()');line=out.split('Reopen this scratch session:\r\n',1)[1].split('\r\n',1)[0].strip();return notice,Path(shlex.split(line)[-1])
def finish(t,name):
 os.write(t.master,b':quit\n');t.read(False);assert t.p.wait(timeout=10)==0;(OUT/(name+'.pty')).write_bytes(t.log);t.close()
trace=OUT/'stale.trace';args=['bwrap','--unshare-user','--uid',str(os.getuid()),'--gid',str(os.getgid()),'--unshare-net','--bind','/','/','--dev','/dev','--proc','/proc','--','strace','-f','-qq','-o',trace,'-e','trace=file,connect',exe,'--no-splash','--color=never']
t=term.Terminal(args,cwd,trapped)
try:
 t.read();notice,manifest=dep(t);assert setup['rev'] in notice and 'acquired' in notice;finish(t,'stale-default')
finally:
 if t.p.poll() is None:t.close()
assert current.read_bytes()==stale and not log.read_text();text=trace.read_text();assert str(store) not in text and 'AF_INET' not in text
# An explicit retained-source override is still the developer path even with a
# stale selection. This is a real path-native build, not a default-source test.
override=E|{'RNX_DEP_RUNTIME':str(installed)};t=term.Terminal([exe,'--no-splash','--color=never'],cwd,override);pid=t.p.pid
try:
 t.read();notice,path_manifest=dep(t);assert 'Runtime: override '+str(installed) in notice
 assert Path('/proc',str(pid),'exe').resolve().parent.name=='artifacts';artifact=Path('/proc',str(pid),'exe').resolve();finish(t,'explicit-override')
finally:
 if t.p.poll() is None:t.close()
assert current.read_bytes()==stale;declaration=path_manifest.read_text();assert str(installed) in declaration and 'git =' not in declaration
lock=json.loads(path_manifest.with_name('rnx.lock').read_text());assert 'tree' in json.dumps(lock)
for name,p in [('git-declaration',manifest),('path-declaration',path_manifest),('path-lock',path_manifest.with_name('rnx.lock'))]:shutil.copy2(p,OUT/(name+'.txt'))
(OUT/'result.json').write_text(json.dumps({'installed_source':str(installed),'original_selection':json.loads(original),'stale_selection':selection,'stale_refuses_show':True,'default_ignores_stale_store':True,'default_compilation_trapped':True,'default_network_disabled':True,'default_store_not_consulted':True,'selection_unchanged':True,'explicit_override_works':True,'path_manifest':str(path_manifest),'path_artifact':str(artifact),'path_artifact_sha256':sha(artifact),'same_pid':pid,'reaped':not Path('/proc',str(pid)).exists()},indent=2)+'\n');print('selection and override passed',flush=True)

import gzip
trace.with_suffix(".trace.gz").write_bytes(gzip.compress(trace.read_bytes(),mtime=0));trace.unlink()
