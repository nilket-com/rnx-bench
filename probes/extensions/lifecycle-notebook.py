"""Record 0053: lifecycle through the unchanged Jupyter kernel and an app worker."""
import json, os, pathlib, shutil, sys, time
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/lifecycle-0053';OUT.mkdir(parents=True,exist_ok=True)
os.environ['RNX_NOTEBOOK_RESULTS']=str(OUT)
sys.path.insert(0,str(ROOT/'probes/jupyter-notebook'))
from common import Environment
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
app=ROOT/'probes/extensions/target/release/lifecycle'
e=Environment();manager=None;client=None;results={}
try:
    shutil.copy2(app,e.worker)
    installed=e.install();assert installed.returncode==0,installed.stderr
    manager=KernelManager(kernel_name='rnx',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(e.root/'data/kernels')]))
    manager.start_kernel(env=e.env,cwd=str(e.notebooks))
    client=manager.client();client.start_channels();client.wait_for_ready(timeout=15)
    replies={}
    def reply(request):
        if request in replies:return replies.pop(request)
        while True:
            msg=client.get_shell_msg(timeout=15)
            parent=msg.get('parent_header',{}).get('msg_id')
            if parent==request:return msg['content']
            replies[parent]=msg['content']
    def execute(source):
        request=client.execute(source)
        response=reply(request)
        response['observed_text']=[]
        while True:
            msg=client.get_iopub_msg(timeout=15)
            if msg.get('parent_header',{}).get('msg_id')!=request:continue
            if msg['header']['msg_type']=='execute_result':response['observed_text'].append(msg['content']['data']['text/plain'])
            if msg['header']['msg_type']=='status' and msg['content']['execution_state']=='idle':break
        return response
    results['declare']=execute('let kept=42; let q=fixture::pending(false);')
    assert results['declare']['status']=='ok'
    request=client.execute('let timer=time::sleep(120000); select { _ = q => (), _ = timer => () };')
    # Wait for the real native operation to be polled, not an elapsed guess.
    while True:
        msg=client.get_iopub_msg(timeout=15)
        if msg.get('parent_header',{}).get('msg_id')==request and msg['header']['msg_type']=='stream' and 'lifecycle opened' in msg['content']['text']:break
    manager.interrupt_kernel()
    results['interrupt']=reply(request);assert results['interrupt']['status']=='error'
    results['repoll']=execute('q.await');assert results['repoll']['status']=='ok' and results['repoll']['observed_text']==['Err("operation cancelled")']
    results['binding']=execute('kept');assert results['binding']['status']=='ok' and results['binding']['observed_text']==['42']
    assert execute('let q=fixture::pending(true);')['status']=='ok'
    bad=client.execute('let timer=time::sleep(5); select { _ = q => (), _ = timer => () }; time::sleep(500).await?; panic!("stop");',stop_on_error=False)
    queued=client.execute('42',stop_on_error=False)
    results['destructor']=reply(bad)
    results['queued']=reply(queued)
    assert results['destructor']['status']=='error',results
    assert results['queued']['ename']=='WorkerDied',results
    (OUT/'notebook.json').write_text(json.dumps(results,indent=2)+'\n')
finally:
    if client:client.stop_channels()
    if manager:
        if manager.has_kernel:manager.shutdown_kernel(now=False)
        manager.cleanup_resources()
    e.close()
print('Jupyter tracked interruption, retained binding, destructor state loss and queued WorkerDied passed')
