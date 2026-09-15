"""Install the assembled worker, execute a notebook, then restart via Jupyter."""
import os,pathlib,sys,shutil,json
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/extensions-0051'
os.environ['RNX_NOTEBOOK_RESULTS']=str(OUT)
sys.path.insert(0,str(ROOT/'probes/jupyter-notebook'))
from common import Environment
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient
import nbformat
app=pathlib.Path(sys.argv[1]).resolve()
e=Environment()
manager=None
try:
    shutil.copy2(app,e.worker)
    installed=e.install()
    assert installed.returncode==0,installed.stderr
    (OUT/'install.log').write_text(installed.stdout+installed.stderr)
    manager=KernelManager(kernel_name='rnx',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(e.root/'data/kernels')]))
    manager.start_kernel(env=e.env,cwd=str(e.notebooks))
    client=manager.client();client.start_channels();client.wait_for_ready(timeout=15)
    def execute(source):
        request=client.execute(source)
        outputs=[]
        while True:
            m=client.get_iopub_msg(timeout=15)
            if m.get('parent_header',{}).get('msg_id')!=request:continue
            kind=m['header']['msg_type']
            if kind in ['execute_result','error','stream']:outputs.append(m['content'])
            if kind=='status' and m['content']['execution_state']=='idle':break
        while True:
            reply=client.get_shell_msg(timeout=15)
            if reply.get('parent_header',{}).get('msg_id')==request:break
        return outputs,reply['content']
    before,reply=execute('let saved = 7; fixture::answer()')
    assert reply['status']=='ok' and before[0]['data']['text/plain']=='42',(before,reply)
    client.stop_channels();manager.restart_kernel(now=False)
    client=manager.client();client.start_channels();client.wait_for_ready(timeout=15)
    after,reply=execute('fixture::answer()');assert reply['status']=='ok' and after[0]['data']['text/plain']=='42'
    missing,reply=execute('saved');assert reply['status']=='error'
    (OUT/'notebook-restart.json').write_text(json.dumps({'before':before,'after':after,'fresh_binding':missing},indent=2)+'\n')
    client.stop_channels();manager.shutdown_kernel(now=False);manager.cleanup_resources();manager=None
    notebook=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(s) for s in ['fixture::answer()', 'fixture::later(20).await?', 'let saved = 3;', 'saved + fixture::answer()']])
    manager=KernelManager(kernel_name='rnx',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(e.root/'data/kernels')]))
    NotebookClient(notebook,km=manager,timeout=15,resources={'metadata':{'path':str(e.notebooks)}}).execute(env=e.env)
    assert notebook.cells[0].outputs[0].data['text/plain']=='42'
    assert notebook.cells[3].outputs[0].data['text/plain']=='45'
    nbformat.validate(notebook);nbformat.write(notebook,OUT/'extensions.ipynb')
    nbformat.validate(nbformat.read(OUT/'extensions.ipynb',as_version=4))
finally:
    if manager:
        if manager.has_kernel:manager.shutdown_kernel(now=False)
        manager.cleanup_resources()
    e.close()
print('isolated installation, notebook validation and restart passed')
