import requests,nbformat,signal,socket
from playwright.sync_api import sync_playwright
from common import *
e=Environment();server=None
try:
    p=e.install();assert p.returncode==0,p.stderr
    book=nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell('# Rune, in a notebook\nPersistent values, ordinary output and named errors — through the rnx worker.'),nbformat.v4.new_code_cell('let base = 40;'),nbformat.v4.new_code_cell('println("Hello from rnx"); base + 2'),nbformat.v4.new_code_cell('1.missing()')])
    nbformat.write(book,e.notebooks/'Journey.ipynb')
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    url=f'http://127.0.0.1:{port}';token='rnx-fixture-only'
    errors=open(OUT/'jupyterlab-server.txt','w')
    server=subprocess.Popen([str(VENV/'bin/jupyter'),'lab','--no-browser','--ServerApp.ip=127.0.0.1',f'--ServerApp.port={port}','--ServerApp.port_retries=0',f'--ServerApp.root_dir={e.notebooks}',f'--IdentityProvider.token={token}','--LabApp.expose_app_in_browser=True',"--ServerApp.jpserver_extensions={'jupyter_lsp': False}"],env=e.env,stdout=errors,stderr=errors)
    end=time.monotonic()+25
    while True:
        assert server.poll() is None,'JupyterLab exited'
        try:
            if requests.get(url+'/api',params={'token':token},timeout=.5).ok:break
        except requests.RequestException:pass
        assert time.monotonic()<end;time.sleep(.1)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.goto(url+'/lab/tree/Journey.ipynb?token='+token)
        page.wait_for_function('window.jupyterapp && window.jupyterapp.shell.currentWidget',timeout=30000)
        page.evaluate("async () => { await window.jupyterapp.shell.currentWidget.context.ready; }")
        page.wait_for_function('window.jupyterapp.shell.currentWidget.content.widgets.length === 4')
        page.locator('.jp-Dialog select').wait_for()
        page.locator('.jp-Dialog select').select_option(label='Rune (rnx)')
        page.locator('.jp-Dialog .jp-mod-accept').click()
        page.wait_for_function("window.jupyterapp.shell.currentWidget.sessionContext.session?.kernel?.name === 'rnx'")
        page.evaluate("async () => { await window.jupyterapp.commands.execute('notebook:run-all-cells'); }")
        page.wait_for_function("window.jupyterapp.shell.currentWidget.content.widgets[3].model.outputs.length > 0")
        body=page.locator('body').inner_text();assert 'Hello from rnx' in body and '42' in body and 'no method' in body,body
        page.screenshot(path=str(OUT/'cells-and-error.png'))
        # A real running cell, then page reload/reconnect while its worker is pending.
        page.evaluate("async () => { let w=window.jupyterapp.shell.currentWidget; w.content.widgets[3].model.sharedModel.setSource('time::sleep(10000).await?'); w.content.activeCellIndex=3; await w.context.save(); window.rnxRun=window.jupyterapp.commands.execute('notebook:run-cell'); }")
        page.wait_for_function("window.jupyterapp.shell.currentWidget.sessionContext.session.kernel.status === 'busy'")
        page.evaluate("() => { window.rnxInfo=window.jupyterapp.shell.currentWidget.sessionContext.session.kernel.requestKernelInfo(); }")
        assert page.evaluate("window.jupyterapp.shell.currentWidget.sessionContext.session.kernel.status")=='busy'
        page.reload()
        page.wait_for_function("window.jupyterapp?.shell.currentWidget?.sessionContext?.session?.kernel?.connectionStatus === 'connected'",timeout=10000)
        assert page.evaluate("window.jupyterapp.shell.currentWidget.sessionContext.session.kernel.status") != 'idle'
        page.screenshot(path=str(OUT/'reconnected-while-busy.png'))
        page.evaluate("async () => { await window.jupyterapp.commands.execute('notebook:interrupt-kernel'); }")
        page.wait_for_function("window.jupyterapp.shell.currentWidget.sessionContext.session.kernel.status === 'idle'")
        # Reload cannot recreate the old client's cell future. Exercise visible
        # interrupt output on a new cell request owned by this page.
        page.evaluate("() => { let w=window.jupyterapp.shell.currentWidget; w.content.activeCellIndex=3; window.rnxRun=window.jupyterapp.commands.execute('notebook:run-cell'); }")
        page.wait_for_function("window.jupyterapp.shell.currentWidget.sessionContext.session.kernel.status === 'busy'")
        page.evaluate("async () => { await window.jupyterapp.commands.execute('notebook:interrupt-kernel'); }")
        page.wait_for_function("window.jupyterapp.shell.currentWidget.content.widgets[3].model.outputs.toJSON().some(x=>x.ename === 'Interrupted')")
        assert 'interrupted' in page.locator('body').inner_text().lower()
        page.screenshot(path=str(OUT/'interrupted.png'))
        # Use the frontend restart command and its confirmation dialog.
        page.evaluate("() => { window.rnxRestart=window.jupyterapp.commands.execute('notebook:restart-kernel'); }")
        page.locator('.jp-Dialog .jp-mod-accept').click()
        page.evaluate("async () => { await window.rnxRestart; }")
        page.evaluate("async () => { let w=window.jupyterapp.shell.currentWidget; w.content.widgets[3].model.sharedModel.setSource('base'); w.content.activeCellIndex=3; await window.jupyterapp.commands.execute('notebook:run-cell'); }")
        page.wait_for_function("window.jupyterapp.shell.currentWidget.content.widgets[3].model.outputs.length > 0")
        assert 'base' in page.locator('body').inner_text() and 'error' in page.locator('body').inner_text().lower()
        outputs=page.evaluate("window.jupyterapp.shell.currentWidget.content.widgets[3].model.outputs.toJSON()")
        assert outputs[0]['output_type']=='error' and 'base' in outputs[0]['evalue'],outputs
        # Restore the example and re-execute in the fresh kernel before saving.
        page.evaluate("async () => { let w=window.jupyterapp.shell.currentWidget; w.content.widgets[3].model.sharedModel.setSource('1.missing()'); await window.jupyterapp.commands.execute('notebook:run-all-cells'); await w.context.save(); }")
        saved=nbformat.read(e.notebooks/'Journey.ipynb',as_version=4)
        assert saved.cells[2].outputs[1].data['text/plain']=='42'
        nbformat.validate(saved)
        nbformat.write(saved,OUT/'Journey.ipynb')
        page.reload()
        page.wait_for_function("window.jupyterapp?.shell.currentWidget?.content?.widgets?.[2]?.model.outputs.length === 2")
        assert '42' in page.locator('body').inner_text()
        page.screenshot(path=str(OUT/'saved-and-reopened.png'))
        log('jupyterlab_select_execute_reconnect_busy_interrupt_restart_save_reopen',passed=True,browser=browser.version)
        browser.close()
finally:
    if server and server.poll() is None:
        try:requests.post(url+'/api/shutdown',headers={'Authorization':'token '+token},timeout=5)
        except requests.RequestException:server.terminate()
        try:server.wait(timeout=10)
        except subprocess.TimeoutExpired:server.kill();server.wait()
    if server:errors.close()
    e.close()
