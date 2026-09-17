#!/usr/bin/env python3
"""0058 gate 4: real project commands and the generated notebook worker."""
import hashlib,json,os,pathlib,shutil,subprocess,sys,tempfile,time
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1];ROOT=BENCH.parent/'rnx'
OUT=BENCH/'results/polars-assembly-0058';OUT.mkdir(parents=True,exist_ok=True)
TOOL=ROOT/'tools/project/target/release/rnx-project';APP=ROOT/'adapters/polars/target/release/rnx-polars';TEST=HERE/'target/rnx-polars-test'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_','POLARS_'))}
ENV.update(TERM='xterm',NO_COLOR='1',POLARS_MAX_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
expected='DataFrame: 2 rows × 2 columns\n"category": string | "total": i64\n"a" | 2\n"🦀" | 7\n'
results={}
def call(name,args,env=ENV,cwd=None,stdin=None,ok=True,timeout=60):
 p=subprocess.run([str(v) for v in args],env=env,cwd=cwd,input=stdin,capture_output=True,text=True,timeout=timeout)
 (OUT/(name+'.log')).write_text(p.stdout+p.stderr)
 assert (p.returncode==0)==ok,(name,p.returncode,p.stdout,p.stderr)
 return p
with tempfile.TemporaryDirectory(prefix='rnx-polars-assembly-') as temp:
 work=pathlib.Path(temp);project=work/'project';project.mkdir();ENV.update(RNX_CONFIG=str(work/'absent'),RNX_HISTORY=str(work/'history'))
 shutil.copy2(BENCH/'examples/polars/main.rn',project/'main.rn')
 manifest=(BENCH/'examples/polars/rnx.toml').read_text().replace('../../../rnx',str(ROOT))
 (project/'rnx.toml').write_text(manifest)
 # Seed compilation objects only, never generated locks or receipts.
 target=project/'.rnx/target';target.mkdir(parents=True)
 subprocess.run(['cp','-a','--reflink=auto',str(ROOT/'adapters/polars/target/release'),str(target/'release')],check=True)
 call('lock',[TOOL,'lock','--manifest',project/'rnx.toml','--offline'],timeout=180)
 call('build',[TOOL,'build','--manifest',project/'rnx.toml','--offline'],timeout=900)
 receipt=json.loads((project/'.rnx/receipt.json').read_text());artifact=project/'.rnx/artifacts'/receipt['executable_sha256']
 assert hashlib.sha256(artifact.read_bytes()).hexdigest()==receipt['executable_sha256']
 results['receipt']=receipt
 for name in ['rnx.toml','rnx.lock','rnx.Cargo.lock']:shutil.copy2(project/name,OUT/name)
 assembly=next((project/'.rnx').rglob('src/main.rs')).parent.parent
 for src,dst in [('Cargo.toml','generated-Cargo.toml'),('src/main.rs','generated-main.rs')]:shutil.copy2(assembly/src,OUT/dst)
 generated=(assembly/'src/main.rs').read_text()
 assert '.with("polars", native_0::build)' in generated and 'main_with' in generated,generated
 metadata=call('metadata',['cargo','metadata','--locked','--offline','--format-version','1','--manifest-path',assembly/'Cargo.toml']).stdout
 graph=json.loads(metadata);packages={p['id']:p for p in graph['packages']}
 (OUT/'resolved-graph.json').write_text(json.dumps({'packages':[{k:p[k] for k in ['id','name','version','source','license','manifest_path']} for p in graph['packages']],'resolve':graph['resolve']},indent=2)+'\n')
 (OUT/'metadata.log').unlink()
 polars=next(n for n in graph['resolve']['nodes'] if packages[n['id']]['name']=='polars')
 accepted=json.loads((BENCH/'results/polars-contract-0058/resolved-graph.json').read_text())
 accepted_packages={p['id']:p for p in accepted['packages']}
 accepted_polars=next(n for n in accepted['resolve']['nodes'] if accepted_packages[n['id']]['name']=='polars')
 assert packages[polars['id']]['version']=='0.55.2' and polars['features']==accepted_polars['features'],polars['features']
 results['polars_features']=polars['features']
 data=work/'data';data.mkdir()
 p=call('project-run',[TOOL,'run','--manifest',project/'rnx.toml','--',data]);assert p.stdout==expected+'\n' and not p.stderr,p.stdout
 results['project_preview']=p.stdout
 # Direct artifact is the assembly control, not a second project invocation.
 direct=work/'direct';direct.mkdir()
 p=call('generated-run',[artifact,'run',project/'main.rn',direct]);assert p.stdout==expected+'\n' and not p.stderr,p.stdout
 path=json.dumps(str(data/'tiny.parquet'))
 source='{ let f=polars::read_parquet('+path+').unwrap(); let bad=f.lazy().sort(["missing"]).unwrap().collect(); assert!(bad.is_err()); let s=f.preview().unwrap(); assert!(s==f.preview().unwrap()); println!("{}",s); () }'
 for name,exe in [('ordinary',APP),('generated',artifact)]:
  p=call(name+'-eval',[exe,'eval',source]);assert p.stdout==expected+'\n' and not p.stderr
  promoted=source.replace('{ let f=', '{ time::sleep(0).await; let f=',1)
  p=call(name+'-async-eval',[exe,'eval',promoted]);assert p.stdout==expected+'\n' and not p.stderr
  session='let f=polars::read_parquet('+path+').unwrap();\nf.lazy().sort(["missing"]).unwrap().collect()\nprintln!("{}",f.preview().unwrap());\n:reset\npolars::lit(1).is_ok()\nf\n:q\n'
  p=call(name+'-session',[exe],stdin=session);assert expected in p.stdout and 'true' in p.stdout and 'missing' in p.stdout
  assert 'No local variable `f`' in p.stderr,p.stderr
  results[name+'-session-reset']=True
  # Marker env is ignored by both ordinary executables.
  marker=work/(name+'-ignored');env=dict(ENV,RNX_POLARS_BUILD_MARKER=str(marker))
  call(name+'-marker-absent',[exe,'eval','polars::lit(1).is_ok()'],env=env);assert not marker.exists()
 stock=call('stock-refusal',[ROOT/'target/release/rnx','eval','polars::lit(1)'],ok=False);assert 'polars' in stock.stderr
 marker=work/'builder';testenv=dict(ENV,RNX_POLARS_BUILD_MARKER=str(marker))
 for command in ['version','help','selfcheck']:
  call('builder-'+command,[TEST,command],env=testenv);assert not marker.exists()
 config=work/'config.rn';config.write_text('polars::col("v"); #{splash:false}')
 testenv['RNX_CONFIG']=str(config)
 p=call('pure-settings',[TEST],env=testenv,stdin='polars::lit(1).is_ok()\n:reset\npolars::lit(2).is_ok()\n:q\n')
 assert 'polars' in p.stderr and 'config' in p.stderr and p.stdout.count('true')==2,(p.stdout,p.stderr)
 assert marker.read_text()=='polars builder\n',marker.read_text()
 results['builder']={'version_help_selfcheck':0,'settings_cannot_resolve_extension':True,'session_including_reset':1}
 # Install this generated artifact as a worker into the existing isolated harness.
 os.environ['RNX_NOTEBOOK_RESULTS']=str(OUT)
 sys.path.insert(0,str(BENCH/'probes/jupyter-notebook'))
 from common import Environment
 from jupyter_client import KernelManager
 from jupyter_client.kernelspec import KernelSpecManager
 import nbformat
 e=Environment();manager=None;client=None;kernel_pids=[];worker_pids=[]
 notebook=nbformat.v4.new_notebook(metadata={'kernelspec':{'name':'rnx','display_name':'Rune (rnx)','language':'rune'}})
 try:
  e.env.update(POLARS_MAX_THREADS='2',TERM='xterm',NO_COLOR='1')
  shutil.copy2(artifact,e.worker)
  installed=e.install();assert installed.returncode==0,installed.stderr
  (OUT/'install.log').write_text(installed.stdout+installed.stderr)
  spec=json.loads((e.root/'data/kernels/rnx/kernel.json').read_text());results['kernelspec']=spec
  manager=KernelManager(kernel_name='rnx',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(e.root/'data/kernels')]))
  manager.start_kernel(env=e.env,cwd=str(e.notebooks))
  def connected():
   c=manager.client();c.start_channels();c.wait_for_ready(timeout=30)
   pid=manager.provisioner.pid;kernel_pids.append(pid)
   children=pathlib.Path(f'/proc/{pid}/task/{pid}/children').read_text().split();worker_pids.extend(map(int,children))
   return c
  client=connected()
  def execute(source,ok=True):
   mid=client.execute(source);outputs=[]
   while True:
    msg=client.get_iopub_msg(timeout=30)
    if msg.get('parent_header',{}).get('msg_id')!=mid:continue
    kind=msg['header']['msg_type'];content=msg['content']
    if kind in ['error','execute_result','stream','display_data']:outputs.append(nbformat.v4.new_output(kind,**content))
    if kind=='status' and content['execution_state']=='idle':break
   while True:
    reply=client.get_shell_msg(timeout=30)
    if reply.get('parent_header',{}).get('msg_id')==mid:break
   assert (reply['content']['status']=='ok')==ok,(source,reply,outputs)
   notebook.cells.append(nbformat.v4.new_code_cell(source,execution_count=reply['content']['execution_count'],outputs=outputs))
   return outputs
  execute('let f=polars::read_parquet('+path+').unwrap(); let saved=7;')
  bad=execute('f.lazy().sort(["missing"]).unwrap().collect().unwrap()',False);assert 'missing' in str(bad)
  shown=execute('println!("{}",f.preview().unwrap());');assert any(o.get('text')==expected+'\n' for o in shown),shown
  opaque=execute('f');assert 'DataFrame' in str(opaque) and 'category' not in str(opaque)
  client.stop_channels();manager.restart_kernel(now=False);client=connected()
  execute('saved',False)
  shown=execute('let fresh=polars::read_parquet('+path+').unwrap(); println!("{}",fresh.preview().unwrap());');assert any(o.get('text')==expected+'\n' for o in shown),shown
  nbformat.validate(notebook);nbformat.write(notebook,OUT/'polars.ipynb');nbformat.validate(nbformat.read(OUT/'polars.ipynb',as_version=4))
  results['notebook']={'failure_recovery':True,'opaque':True,'restart_cleared_binding':True,'extension_survived_restart':True}
 finally:
  if client:client.stop_channels()
  if manager:
   if manager.has_kernel:manager.shutdown_kernel(now=False)
   manager.cleanup_resources()
  e.close()
 assert worker_pids and all(not pathlib.Path('/proc',str(pid)).exists() for pid in kernel_pids+worker_pids),(kernel_pids,worker_pids)
 results['cleanup']={'kernel_pids':kernel_pids,'worker_pids':worker_pids,'all_reaped':True}
 results['visible_files']=sorted(p.name for p in project.iterdir() if p.name!='.rnx')
 assert results['visible_files']==['main.rn','rnx.Cargo.lock','rnx.lock','rnx.toml']
 results['ordinary_sha256']=hashlib.sha256(APP.read_bytes()).hexdigest();results['test_sha256']=hashlib.sha256(TEST.read_bytes()).hexdigest()
(OUT/'results.json').write_text(json.dumps(results,indent=2,ensure_ascii=False)+'\n')
print('PASS: lock/build/run, generated and ordinary entrypoints, pure settings, builder counts, notebook restart and cleanup')
