#!/usr/bin/env python3
"""Private fixture kernelspec: no user installation and no JupyterLab claim."""
import json,pathlib,tempfile
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from probe import BIN,WORKER,OUT,log
with tempfile.TemporaryDirectory(prefix='rnx nbclient ') as d:
    root=pathlib.Path(d);spec=root/'kernels'/'rnx-fixture';spec.mkdir(parents=True)
    spec.joinpath('kernel.json').write_text(json.dumps(dict(argv=[str(BIN),'--connection-file','{connection_file}','--rnx',str(WORKER)],display_name='Rune (rnx fixture)',language='rune',interrupt_mode='message')))
    manager=KernelManager(kernel_name='rnx-fixture',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(root/'kernels')]))
    notebook=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('let n = 40;'),nbformat.v4.new_code_cell('print!("hello\\n"); n + 2'),nbformat.v4.new_code_cell('1.missing()')])
    client=NotebookClient(notebook,km=manager,timeout=10,allow_errors=True,resources={'metadata':{'path':d}})
    try:client.execute()
    finally:
        if manager.has_kernel:manager.shutdown_kernel(now=False)
        manager.cleanup_resources()
    assert notebook.cells[0].outputs==[]
    assert notebook.cells[1].outputs[0].text=='hello\n'
    assert notebook.cells[1].outputs[1].data['text/plain']=='42'
    assert notebook.cells[2].outputs[0].ename=='RuntimeError'
    nbformat.write(notebook,OUT/'executed.ipynb')
    loaded=nbformat.read(OUT/'executed.ipynb',as_version=4)
    assert loaded.cells[1].outputs[1].data['text/plain']=='42'
    log('nbclient_private_spec_execute_save_reopen',passed=True,jupyterlab=False,user_installation=False)
