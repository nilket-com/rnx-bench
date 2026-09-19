from common import *
import signal,shutil
S=T/'concurrent-source';shutil.copytree(T/'tiny-source-clean',S,ignore=shutil.ignore_patterns('.git'))
(S/'build.rs').write_text('fn main(){if let Ok(p)=std::env::var("FIXTURE_BLOCK"){std::fs::write(std::env::var("FIXTURE_STARTED").unwrap(),b"started").unwrap();while std::path::Path::new(&p).exists(){std::thread::sleep(std::time::Duration::from_millis(10));}}}\n')
git(S,'init','-q');git(S,'add','.');git(S,'commit','-qm','owned blocking compiler fixture');rev=git(S,'rev-parse','HEAD').stdout.decode().strip();rows=[]
def wait_file(p,child=None):
 end=time.monotonic()+30
 while time.monotonic()<end:
  if p.exists():return
  if child and child.poll() is not None:raise AssertionError(child.communicate())
  time.sleep(.01)
 raise AssertionError(('missing marker',p))
def spawn(p,env,label):
 out=(O/(label+'.log')).open('wb');child=subprocess.Popen([str(TOOL),'build','--offline','--manifest',str(p/'rnx.toml')],env=env,stdout=out,stderr=subprocess.STDOUT,start_new_session=True);return child,out
for scenario in ['builder-term','waiter-kill']:
 cache=T/('cache-'+scenario);e=ENV|{'RNX_PROJECT_CACHE':str(cache)}
 apps=[]
 for suffix in ['a','b']:
  p=project(scenario+suffix,S.as_uri(),rev);run([TOOL,'lock','--manifest',p/'rnx.toml'],env=e);apps.append(p)
 lock=json.loads((apps[0]/'rnx.lock').read_text());identity=json.loads(lock['assembly']['identity']);assert lock['assembly']==json.loads((apps[1]/'rnx.lock').read_text())['assembly'];key=run([T/'b3'],data=lock['assembly']['identity'].encode()).stdout.decode().strip();entry=cache/'entries'/key
 block=T/(scenario+'-block');block.write_text('wait');started=T/(scenario+'-started');waiting=T/(scenario+'-waiting')
 builder,bo=spawn(apps[0],e|{'FIXTURE_BLOCK':str(block),'FIXTURE_STARTED':str(started)},scenario+'-builder');waiter=None;wo=None
 try:
  wait_file(started,builder)
  # The production waiter announces the lock wait at its existing support hook.
  waiter,wo=spawn(apps[1],e|{'RNX_CACHE_PAUSE':'waiting','RNX_CACHE_MARKER':str(waiting)},scenario+'-waiter');wait_file(waiting,waiter)
  if scenario=='builder-term':
   builder.send_signal(signal.SIGTERM);assert builder.wait(timeout=10)==143;assert not (entry/'ready.json').exists();assert not (apps[0]/'.rnx/receipt.json').exists();block.unlink();waiting.unlink();assert waiter.wait(timeout=60)==0
  else:
   waiter.kill();assert waiter.wait(timeout=5)==-signal.SIGKILL;block.unlink();assert builder.wait(timeout=60)==0;assert not (apps[1]/'.rnx/receipt.json').exists();run([TOOL,'build','--offline','--manifest',apps[1]/'rnx.toml'],env=e)
  assert (entry/'ready.json').exists();run([TOOL,'eval','--manifest',apps[1]/'rnx.toml','--','42'],env=e)
  rows.append({'case':scenario,'key':key,'ready_format':json.loads((entry/'ready.json').read_text())['format'],'success':True})
 finally:
  for child in [builder,waiter]:
   if child and child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
  bo.close()
  if wo:wo.close()
save('concurrency.json',rows);print('Git-source builder and waiter interruption cases pass',flush=True)
