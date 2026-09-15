"""Install the kernel in isolation and exercise the migrated modules as cells."""
import pathlib,sys,os
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'jupyter-notebook'))
from common import *
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
e=Environment()
try:
 installed=e.install();assert installed.returncode==0,installed.stderr
 sources=[
  'let n = json::parse("18446744073709551615")?;',
  'json::stringify(n)?',
  'io::eprint("tail\\0")?; 42',
  'process::exit(0).is_err()',
  'process::run("/bin/sh", ["-c", "printf out; printf err >&2; exit 7"], #{})?.code',
  'host::json_parse("1")',
  'n == 18446744073709551615u64',
  '1.missing()',
 ]
 manager=KernelManager(kernel_name='rnx',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(e.root/'data/kernels')]))
 book=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(s) for s in sources])
 client=NotebookClient(book,km=manager,timeout=10,allow_errors=True,resources={'metadata':{'path':str(e.notebooks)}})
 try:client.execute(env=e.env)
 finally:
  if manager.has_kernel:manager.shutdown_kernel(now=False)
  manager.cleanup_resources()
 assert book.cells[1].outputs[0].data['text/plain']=='"18446744073709551615"'
 assert book.cells[2].outputs[0].text=='tail\0'
 assert book.cells[3].outputs[0].data['text/plain']=='true'
 assert book.cells[4].outputs[0].data['text/plain']=='7'
 assert book.cells[5].outputs[0].output_type=='error'
 assert book.cells[6].outputs[0].data['text/plain']=='true'
 for cell in book.cells:
  for output in cell.outputs:
   if output.output_type=='error':assert set(output)=={'output_type','ename','evalue','traceback'}
 nbformat.validate(book);nbformat.write(book,OUT/'namespaces.ipynb');nbformat.validate(nbformat.read(OUT/'namespaces.ipynb',as_version=4))
 log('namespace_cells_survive_exit_refusal_and_old_name_failure',passed=True)
finally:e.close()
