"""Failure/recovery in each context, oversize RSS, and notebook save/validate."""
import json, os, pathlib, shutil, subprocess, sys
from cluster import Cluster
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/postgres-0052-adapter'; OUT.mkdir(parents=True,exist_ok=True)
BIN=ROOT.parent/'rnx/adapters/postgres/target/release/rnx-pg'
sys.path.insert(0,str(ROOT.parent/'rnx/tests'))
from worker_parent import Parent
os.environ['RNX_NOTEBOOK_RESULTS']=str(OUT)
sys.path.insert(0,str(ROOT/'probes/jupyter-notebook'))
from common import Environment
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
import nbformat
results={}
with Cluster() as c:
    env=dict(os.environ,TERM='xterm',NO_COLOR='1',RNX_CONFIG=str(c.root/'absent'),RNX_HISTORY=str(c.root/'history'))
    c.sql('CREATE TABLE unique_values(v int8 UNIQUE); INSERT INTO unique_values VALUES(1)')
    def call(sql,params='[]',url=None):
        return f'postgres::query({json.dumps(url or c.url)}, {json.dumps(sql)}, {params}, #{{}}).await'
    failures=[('connect',call('SELECT 1',url='postgresql:///postgres?host=/missing')),
              ('authentication',call('SELECT 1',url=c.url.replace('///','//locked:DISTINCTIVE_PASSWORD_MARKER@/'))),
              ('syntax',call('SELECT ???')), ('unique',call('INSERT INTO unique_values VALUES(1)')),
              ('type',call('SELECT $1::int8','["abc"]'))]
    w=Parent(str(BIN),env)
    try:
        for name,query in failures:
            source='{ let failure=match '+query+' { Ok(_) => "wrong", Err(e) => e }; let next='+call('SELECT 42 AS n')+'?; [failure, next.rows[0].n] }'
            for mode in ['run','eval','session']:
                if mode=='session':
                    r=w.execute(source)[0]; assert r['failure'] is None and '42' in r['text_plain'],r
                    text=r['text_plain']
                else:
                    if mode=='run':
                        path=c.root/'case.rn';path.write_text('pub async fn main(_) { '+source+' }');args=['run',str(path)]
                    else:args=['eval',source]
                    r=subprocess.run([str(BIN),*args],env=env,text=True,capture_output=True,timeout=10)
                    assert r.returncode==0 and not r.stderr,(name,mode,r)
                    text=r.stdout
                assert 'cannot query' in text and 'DISTINCTIVE_PASSWORD_MARKER' not in text,(name,mode,text)
                results[name+' '+mode]=text
    finally:w.close()
    rss=c.root/'rss'
    r=subprocess.run(['/usr/bin/time','-f','%M','-o',str(rss),str(BIN),'eval','match '+call("SELECT repeat('x',16777216) AS v")+' { Ok(_) => "wrong", Err(e) => e }'],env=env,text=True,capture_output=True,timeout=10)
    assert r.returncode==0 and '8388608 bytes at row 1' in r.stdout,(r.stdout,r.stderr)
    results['oversize']=dict(peak_rss_kib=int(rss.read_text()),stdout=r.stdout,stderr=r.stderr)
    e=Environment();manager=None;client=None
    try:
        shutil.copy2(BIN,e.worker)
        installed=e.install(); assert installed.returncode==0,installed.stderr
        manager=KernelManager(kernel_name='rnx',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(e.root/'data/kernels')]))
        manager.start_kernel(env=e.env,cwd=str(e.notebooks))
        client=manager.client();client.start_channels();client.wait_for_ready(timeout=15)
        notebook=nbformat.v4.new_notebook(metadata={'kernelspec':{'name':'rnx','display_name':'rnx','language':'rune'}})
        sources=['match '+call('SELECT ???')+' { Ok(v) => v, Err(e) => panic!("{}", e) }',call('SELECT 42 AS n')+'?']
        for source in sources:
            request=client.execute(source);reply=client.get_shell_msg(timeout=15)
            assert reply['parent_header']['msg_id']==request
            cell=nbformat.v4.new_code_cell(source,execution_count=reply['content']['execution_count'])
            while True:
                msg=client.get_iopub_msg(timeout=15)
                if msg.get('parent_header',{}).get('msg_id')!=request:continue
                kind=msg['header']['msg_type'];content=msg['content']
                if kind in ['error','execute_result','stream','display_data']:
                    cell.outputs.append(nbformat.v4.new_output(kind,**content))
                if kind=='status' and content['execution_state']=='idle':break
            notebook.cells.append(cell)
            results['notebook '+str(len(notebook.cells))]=reply['content']
        assert results['notebook 1']['status']=='error' and '42601' in str(notebook.cells[0].outputs)
        assert results['notebook 2']['status']=='ok' and '42' in str(notebook.cells[1].outputs)
        nbformat.validate(notebook)
        nbformat.write(notebook,OUT/'postgres.ipynb')
        nbformat.validate(nbformat.read(OUT/'postgres.ipynb',as_version=4))
    finally:
        if client:client.stop_channels()
        if manager:
            if manager.has_kernel:manager.shutdown_kernel(now=False)
            manager.cleanup_resources()
        e.close()
    c.wait_idle()
    results['cleanup']=dict(directory=str(c.root),postmaster=c.postmaster)
(OUT/'entrypoints.json').write_text(json.dumps(results,indent=2)+'\n')
print('same-context recovery in run/eval/session/notebook, saved notebook and oversize RSS passed')
