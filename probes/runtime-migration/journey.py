"""Migration with a live old consumer, an old-key kernelspec, and new :dep journeys."""
from pathlib import Path
import os,sys,json,subprocess as sp,shutil,importlib.util,time,hashlib,socket,threading,select
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target/real';O=B/'results/runtime-migration-0065';E=json.loads((W/'env.json').read_text());d=json.loads((W/'setup.json').read_text());T=Path(d['tool']);S=Path(d['launcher']);store=Path(d['store']);entry=store/'entries'/d['old_id'];artifact=Path(d['artifact'])
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
term=load('terminal',B/'probes/project-interactive/common.py')
def snapshot(p):return {str(q.relative_to(p)):(hashlib.sha256(q.read_bytes()).hexdigest(),q.stat().st_mtime_ns,q.stat().st_ino) for q in p.rglob('*') if q.is_file()}
def call(a):
 p=sp.run(list(map(str,a)),env=E,cwd=W,capture_output=True,text=True,timeout=90);assert p.returncode==0,(a,p.stdout,p.stderr);return p
results={};before=snapshot(entry);oldproject=snapshot(Path(d['old_manifest']).parent);oldartifact=hashlib.sha256(artifact.read_bytes()).hexdigest();t=term.Terminal([artifact,'--no-splash','--color=never'],W,E);t.read();assert 'before' in t.send('let held = 42; keep::read()')
os.environ['RNX_NOTEBOOK_RESULTS']=str(O);notebook=load('notebook_fixture',B/'probes/jupyter-notebook/common.py');e=notebook.Environment();e.worker=artifact;e.env.update(POLARS_MAX_THREADS='1');installed=e.install();assert installed.returncode==0,installed.stderr
specpath=e.root/'data/kernels/rnx/kernel.json';spec=specpath.read_bytes();assert str(artifact).encode() in spec;(O/'old-key-kernel.json').write_bytes(spec)
manager=None;client=None
try:
 start=time.monotonic();out=call([T,'runtime','install','--from',entry/'source']);newid=out.stdout.split('runtime ',1)[1].splitlines()[0];new=store/'entries'/newid;assert newid!=d['old_id'];newdoc=json.loads((new/'installation.json').read_text());old=json.loads((entry/'installation.json').read_text());assert newdoc['migrated_from']==dict(format=1,id=d['old_id'])
 for k in ['source_path','source_commit','dirty_tracked']:assert newdoc[k]==old[k]
 assert snapshot(entry)==before and snapshot(Path(d['old_manifest']).parent)==oldproject
 Path(d['retained']).write_text('after migration');assert '42' in t.send('held');assert 'after migration' in t.send('keep::read()');assert hashlib.sha256(artifact.read_bytes()).hexdigest()==oldartifact
 results['migration']=dict(seconds=time.monotonic()-start,old=d['old_id'],new=newid,old_entry_unchanged=True,old_project_unchanged=True)
 # The previously written kernelspec is actually launched after migration.
 from jupyter_client import KernelManager
 from jupyter_client.kernelspec import KernelSpecManager
 manager=KernelManager(kernel_name='rnx',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(e.root/'data/kernels')]))
 manager.start_kernel(env=e.env,cwd=str(e.notebooks));client=manager.client();client.start_channels();client.wait_for_ready(timeout=30);pid=manager.provisioner.pid
 def execute(source):
  mid=client.execute(source);outputs=[]
  while True:
   msg=client.get_iopub_msg(timeout=30)
   if msg.get('parent_header',{}).get('msg_id')!=mid:continue
   if msg['header']['msg_type'] in ['stream','execute_result','error']:outputs.append(msg['content'])
   if msg['header']['msg_type']=='status' and msg['content']['execution_state']=='idle':break
  while True:
   reply=client.get_shell_msg(timeout=30)
   if reply.get('parent_header',{}).get('msg_id')==mid:break
  assert reply['content']['status']=='ok',(source,outputs,reply)
  return outputs
 values=execute('println!("{}",keep::read()); polars::lit(1).is_ok()');assert 'after migration' in str(values) and 'true' in str(values);assert specpath.read_bytes()==spec
 results['old_kernel']=dict(pid=pid,started_after_migration=True,outputs=values,kernelspec_unchanged=True)
 client.stop_channels();client=None;manager.shutdown_kernel(now=False);manager.cleanup_resources();manager=None;assert not Path('/proc',str(pid)).exists()
 # New journeys use an empty second cache; old artifact/OUT_DIR remain owned.
 nw=W/'new';nw.mkdir();(nw/'bin').mkdir();shutil.copy2(T,nw/'bin/rnx-project');shutil.copy2(S,nw/'bin/rnx');env=dict(E,RNX_PROJECT_TOOL=str(nw/'bin/rnx-project'),RNX_PROJECT_CACHE=str(nw/'cache'),XDG_STATE_HOME=str(nw/"state ' private"));(nw/'env.json').write_text(json.dumps(env))
 raw=(B/'probes/session-dogfood/check.py').read_text();raw=raw.replace("R=B.parent/'rnx'",'R=Path('+repr(str(new/'source'))+')')
 needle="assert 'bindings and declarations will be lost' in notice";assert raw.count(needle)==1
 raw=raw.replace(needle,needle+'\n if "New scratch project:" in notice: assert '+repr('Runtime: installation '+newid)+' in notice')
 script=O/'new-dogfood.py';script.write_text(raw)
 with (O/'new-dogfood.log').open('w') as f:p=sp.run([sys.executable,script],env=dict(env,RNX_DOGFOOD_TARGET=str(nw),RNX_DOGFOOD_RESULTS=str(O/'dogfood')),stdout=f,stderr=sp.STDOUT)
 assert p.returncode==0,(O/'new-dogfood.log').read_text()
 assert 'after migration' in t.send('keep::read()');assert '42' in t.send('held');assert snapshot(entry)==before
 assert call([d['old_tool'],'eval','--manifest',d['old_manifest'],'--','keep::read()']).stdout=='"after migration"\n'
 results['old_session']=dict(pid=t.p.pid,bindings_survived=True,retained_output_read_after_new_journeys=True,old_tool_project_still_runs=True)
 results['new_default_journeys']=json.loads((O/'dogfood/matrix.json').read_text())
 results['retained_bytes']={i:sum(q.stat().st_size for q in (store/'entries'/i).rglob('*') if q.is_file()) for i in [d['old_id'],newid]}
 os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=10)==0
 (O/'old-session.pty').write_bytes(t.log);(O/'journey.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS old live session, old-key kernel after migration, and new default journeys',flush=True)
finally:
 if client:client.stop_channels()
 if manager:
  if manager.has_kernel:manager.shutdown_kernel(now=False)
  manager.cleanup_resources()
 e.close();t.close()
