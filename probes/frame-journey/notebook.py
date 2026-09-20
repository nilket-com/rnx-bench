"""The notebook journey through a real kernel: the generated executable installed as the
kernelspec in a private Jupyter environment, driven with jupyter_client; a bare frame, an
error, the retained frame, a restart (fresh worker, bindings gone) and a new frame; the
notebook saved with nbformat, validated and reopened; every kernel and worker reaped.
Runs itself under the jupyter-notebook probe's virtual environment."""
from common import *
import os, sys, shutil, tempfile, time
VENV = B / 'probes/jupyter-notebook/.venv'
if Path(sys.prefix).resolve() != VENV.resolve():
    os.execv(str(VENV / 'bin/python'), [str(VENV / 'bin/python'), *sys.argv])
import nbformat
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager

project = T / 'project'
work = T / 'notebook'
work.mkdir(exist_ok=True)
receipt = json.loads((project / '.rnx/receipt.json').read_text())
artifacts = [p for p in (T / 'cache').glob('entries/*/artifacts/*') if p.stat().st_ino == receipt['stamp']['inode']]
assert len(artifacts) == 1, artifacts
artifact = artifacts[0]
user_kernels = Path.home() / '.local/share/jupyter/kernels'
user_before = sorted((p.name, p.stat().st_mtime_ns) for p in user_kernels.iterdir()) if user_kernels.exists() else None
temp = tempfile.TemporaryDirectory(prefix='rnx frame journey ')
root = Path(temp.name)
binaries = root / 'bin with spaces'
binaries.mkdir()
kernel = binaries / 'rnx-jupyter'
shutil.copy2(KERNEL, kernel)
env = dict(ENV, HOME=str(root), JUPYTER_DATA_DIR=str(root / 'data'), JUPYTER_CONFIG_DIR=str(root / 'config'),
           JUPYTER_RUNTIME_DIR=str(root / 'runtime'), JUPYTER_PREFER_ENV_PATH='0', PATH=str(VENV / 'bin') + os.pathsep + ENV['PATH'])
notebooks = root / 'notebooks'
notebooks.mkdir()
(notebooks / 'sales.csv').write_text(SALES)
installed = run([kernel, 'install', '--rnx', artifact], env=env, timeout=60)
spec = json.loads((root / 'data/kernels/rnx/kernel.json').read_text())
assert str(artifact) in spec['argv'], spec


def workers():
    out = run(['pgrep', '-f', f'^{artifact} worker'], check=False).stdout.decode().split()
    return sorted(int(p) for p in out)


manager = KernelManager(kernel_name='rnx', kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(root / 'data/kernels')]))
cells = []
try:
    manager.start_kernel(env=env, cwd=str(notebooks))
    client = manager.client()
    client.start_channels()
    client.wait_for_ready(timeout=60)

    def execute(source):
        msg_id = client.execute(source)
        outputs = []
        while True:
            msg = client.get_iopub_msg(timeout=60)
            if msg['parent_header'].get('msg_id') != msg_id:
                continue
            kind = msg['msg_type']
            if kind == 'status' and msg['content']['execution_state'] == 'idle':
                break
            if kind in ('execute_result', 'stream', 'error', 'display_data'):
                outputs.append(nbformat.v4.output_from_msg(msg))
        reply = client.get_shell_msg(timeout=60)
        assert reply['parent_header']['msg_id'] == msg_id
        cell = nbformat.v4.new_code_cell(source, outputs=outputs, execution_count=reply['content'].get('execution_count'))
        cells.append(cell)
        return reply['content']['status'], outputs

    first_worker = workers()
    assert len(first_worker) == 1, first_worker
    status, out = execute(f'let sales = polars::read_csv("sales.csv", {SALES_SCHEMA})?;')
    assert status == 'ok' and out == [], out
    status, out = execute('sales')
    assert status == 'ok' and len(out) == 1 and out[0]['output_type'] == 'execute_result', out
    table = out[0]['data']['text/plain']
    assert table.startswith('DataFrame: 5 rows × 4 columns\n') and '"north" | "apple" | 4 | 1.5' in table, table
    assert 'text/html' not in out[0]['data']
    status, out = execute('sales.lazy().filter(polars::col("missing").gt(polars::lit(1)?)).collect()?')
    assert status == 'error' and out and out[-1]['output_type'] == 'error', out
    error_name = out[-1]['ename']
    error_value = out[-1]['evalue']
    status, out = execute('sales')
    assert status == 'ok' and out[0]['data']['text/plain'] == table
    status, out = execute('[sales]')
    assert out[0]['data']['text/plain'] == '[<::polars::DataFrame>]'
    # Restart: a fresh worker process, the old one gone, bindings gone, the presenter present.
    manager.restart_kernel(now=False)
    client.stop_channels()
    client = manager.client()
    client.start_channels()
    client.wait_for_ready(timeout=60)
    deadline = time.time() + 10
    while time.time() < deadline and (first_worker[0] in workers() or not workers()):
        time.sleep(0.1)
    second_worker = workers()
    assert len(second_worker) == 1 and second_worker != first_worker, (first_worker, second_worker)
    status, out = execute('sales')
    assert status == 'error', out
    status, out = execute(f'polars::read_csv("sales.csv", {SALES_SCHEMA})?')
    assert status == 'ok' and out[0]['data']['text/plain'] == table, out
finally:
    if manager.has_kernel:
        manager.shutdown_kernel(now=False)
    manager.cleanup_resources()
book = nbformat.v4.new_notebook(cells=cells, metadata={'kernelspec': {'name': 'rnx', 'display_name': spec['display_name'], 'language': spec['language']}})
nbformat.validate(book)
O.mkdir(parents=True, exist_ok=True)
nbformat.write(book, O / 'journey.ipynb')
reopened = nbformat.read(O / 'journey.ipynb', as_version=4)
nbformat.validate(reopened)
assert reopened.cells[1].outputs[0].data['text/plain'] == table
deadline = time.time() + 10
while time.time() < deadline and workers():
    time.sleep(0.1)
assert not workers(), workers()
assert not run(['pgrep', '-f', str(kernel)], check=False).stdout
user_after = sorted((p.name, p.stat().st_mtime_ns) for p in user_kernels.iterdir()) if user_kernels.exists() else None
assert user_before == user_after
temp.cleanup()
save('notebook.json', {'artifact': str(artifact), 'kernelspec': spec, 'first_worker': first_worker, 'second_worker': second_worker,
                       'error_name': error_name, 'error_value': error_value, 'cells': [{'source': c.source, 'execution_count': c.execution_count,
                                                             'outputs': [(o['output_type'], o.get('data', {}).get('text/plain', o.get('ename', o.get('text', ''))))
                                                                         for o in c.outputs]} for c in cells]})
print('notebook journey: bare frame as text/plain, error, retained frame, restart with a fresh worker, new frame; notebook validated and reopened; kernels and workers reaped', flush=True)
