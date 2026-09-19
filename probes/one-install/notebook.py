from common import *
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
import nbformat
out=O/'notebook';out.mkdir();os.environ['RNX_NOTEBOOK_RESULTS']=str(out)
j=load('notebook_environment',B/'probes/jupyter-notebook/common.py')
journey=json.loads((O/'published/journey.json').read_text());artifact=Path(journey['combined']['artifact']);path=json.dumps(str(T/'published/caller/combined.parquet'))
e=j.Environment();manager=None;client=None;pids=[]
book=nbformat.v4.new_notebook(metadata={'kernelspec':{'name':'rnx','display_name':'Rune (rnx)','language':'rune'}})
try:
 e.env.update(POLARS_MAX_THREADS='1',TERM='xterm-256color',NO_COLOR='1');shutil.copy2(artifact,e.worker)
 installed=e.install();assert installed.returncode==0,installed.stderr;(out/'install.log').write_text(installed.stdout+installed.stderr)
 spec=json.loads((e.root/'data/kernels/rnx/kernel.json').read_text())
 manager=KernelManager(kernel_name='rnx',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(e.root/'data/kernels')]))
 manager.start_kernel(env=e.env,cwd=str(e.notebooks))
 def connect():
  c=manager.client();c.start_channels();c.wait_for_ready(timeout=30);pid=manager.provisioner.pid;pids.append(pid);pids.extend(map(int,Path(f'/proc/{pid}/task/{pid}/children').read_text().split()));return c
 client=connect()
 def execute(source,ok=True):
  mid=client.execute(source);outputs=[]
  while True:
   m=client.get_iopub_msg(timeout=30)
   if m.get('parent_header',{}).get('msg_id')!=mid:continue
   kind=m['header']['msg_type'];content=m['content']
   if kind in ['error','execute_result','stream','display_data']:outputs.append(nbformat.v4.new_output(kind,**content))
   if kind=='status' and content['execution_state']=='idle':break
  while True:
   reply=client.get_shell_msg(timeout=30)
   if reply.get('parent_header',{}).get('msg_id')==mid:break
  assert (reply['content']['status']=='ok')==ok,(source,reply,outputs)
  book.cells.append(nbformat.v4.new_code_cell(source,execution_count=reply['content']['execution_count'],outputs=outputs));return outputs
 execute('let f=polars::read_parquet('+path+').unwrap(); let saved=7;')
 assert 'missing' in str(execute('f.lazy().sort(["missing"]).unwrap().collect().unwrap()',False))
 shown=execute('println!("{}",f.preview().unwrap());');assert '"a" | 2' in str(shown) and '🦀' in str(shown)
 opaque=execute('f');assert 'DataFrame' in str(opaque) and 'category' not in str(opaque)
 client.stop_channels();manager.restart_kernel(now=False);client=connect();execute('saved',False)
 fresh=execute('let f=polars::read_parquet('+path+').unwrap(); println!("{}",f.preview().unwrap());');assert fresh==shown
 nbformat.validate(book);nbformat.write(book,out/'polars.ipynb');nbformat.validate(nbformat.read(out/'polars.ipynb',as_version=4))
finally:
 if client:client.stop_channels()
 if manager:
  if manager.has_kernel:manager.shutdown_kernel(now=False)
  manager.cleanup_resources()
 e.close()
assert len(pids)>=4 and all(not Path('/proc',str(p)).exists() for p in pids)
(out/'result.json').write_text(json.dumps({'artifact':str(artifact),'artifact_sha256':sha(artifact),'kernel_sha256':sha(R/'jupyter/target/release/rnx-jupyter'),'kernelspec':spec,'pids':pids,'all_reaped':True,'error_recovery':True,'restart':True,'opaque_frame':True,'saved_valid_notebook':True},indent=2)+'\n');print('notebook passed')
