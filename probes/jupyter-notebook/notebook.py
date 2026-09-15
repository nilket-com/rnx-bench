import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from common import *
e=Environment()
try:
    installed=e.install();assert installed.returncode==0,installed.stderr
    manager=KernelManager(kernel_name='rnx',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(e.root/'data/kernels')]))
    book=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('let a = 40;'),nbformat.v4.new_code_cell('println("hello"); a + 2'),nbformat.v4.new_code_cell('1.missing()')])
    client=NotebookClient(book,km=manager,timeout=10,allow_errors=True,resources={'metadata':{'path':str(e.notebooks)}})
    try:client.execute(env=e.env)
    finally:
        if manager.has_kernel:manager.shutdown_kernel(now=False)
        manager.cleanup_resources()
    assert book.cells[0].outputs==[] and book.cells[1].outputs[0].text=='hello\n'
    assert book.cells[1].outputs[1].data['text/plain']=='42'
    assert book.cells[2].outputs[0].ename=='RuntimeError'
    nbformat.write(book,OUT/'nbclient.ipynb')
    assert nbformat.read(OUT/'nbclient.ipynb',as_version=4).cells[1].outputs[1].data['text/plain']=='42'
    log('installed_nbclient_execute_save_reopen',passed=True)
finally:e.close()
