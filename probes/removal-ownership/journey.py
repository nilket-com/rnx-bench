"""Actual old/current storage; live retained-output consumers stop before deletion."""
from pathlib import Path
import os, sys, json, subprocess as sp, importlib.util, time, hashlib, fcntl, stat

H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target/real';O=Path(os.environ.get('RNX_REMOVAL_RESULTS',str(B/'results/removal-ownership-0066'))).resolve();O.mkdir(parents=True,exist_ok=True)
E=json.loads((W/'env.json').read_text());d=json.loads((W/'setup.json').read_text())
P=H/'target/tool/target/release/rnx-removal-probe';T=Path(d['tool']);store=Path(d['store'])
old=store/'entries'/d['old_id'];artifact=Path(d['artifact']);cache=Path(E['RNX_PROJECT_CACHE'])
cache_entry=artifact.parent.parent;key=cache_entry.name;retained=Path(d['retained'])
assert retained.is_relative_to(cache_entry) and not (W/'original').exists()
assert not (O/'journey.json').exists(),'fresh real setup required'
def call(a,ok=True):
    p=sp.run(list(map(str,a)),env=E,cwd=W,capture_output=True,text=True,timeout=1200)
    assert (p.returncode==0)==ok,(a,p.returncode,p.stdout,p.stderr)
    return p
def snap(root,contents=False):
    out={}
    for base,dirs,files in os.walk(root,followlinks=False):
        for n in dirs+files:
            p=Path(base)/n;s=p.lstat();digest=None
            if stat.S_ISREG(s.st_mode) and contents:digest=hashlib.sha256(p.read_bytes()).hexdigest()
            elif stat.S_ISLNK(s.st_mode):digest=os.readlink(p)
            out[str(p.relative_to(root))]=(s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,digest)
    return out
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
results={}
# Migrate with the real current product, keeping the old source and artifact.
before=snap(old,True);r=call([T,'runtime','install','--from',old/'source']);newid=r.stdout.split('runtime ',1)[1].splitlines()[0]
new=store/'entries'/newid;assert newid!=d['old_id'] and snap(old,True)==before
assert json.loads((new/'installation.json').read_text())['format']==2
results['runtime_formats']={'old':1,'new':2,'migration_preserved_old':True}
# A genuine current ready document and artifact, independently compiled, are kept.
project=W/'new-project';project.mkdir();manifest=project/'rnx.toml'
(project/'entry.rn').write_text('pub fn main(_) { polars::lit(1).is_ok() }\n')
manifest.write_text('format=1\n[application]\nentry="entry.rn"\n[runtime]\npath='+json.dumps(str(new/'source'))+'\n')
call([T,'add','polars','--manifest',manifest]);call([T,'lock','--offline','--manifest',manifest])
start=time.monotonic();r=call([T,'build','--offline','--manifest',manifest]);(O/'new-build.log').write_text(r.stdout+r.stderr)
rec=json.loads((project/'.rnx/receipt.json').read_text());newkey=rec['assembly_key'];assert newkey!=key
results['current_build']={'seconds':time.monotonic()-start,'key':newkey,'receipt_format':rec['format']}
print('PASS current assembly alongside old-key assembly',flush=True)

term=load('terminal',B/'probes/project-interactive/common.py');t=None;e=None;manager=None;client=None
try:
    t=term.Terminal([artifact,'--no-splash','--color=never'],W,E);t.read();assert 'before' in t.send('let held = 42; keep::read()')
    os.environ['RNX_NOTEBOOK_RESULTS']=str(O);nb=load('notebook_fixture',B/'probes/jupyter-notebook/common.py');e=nb.Environment();e.worker=artifact;e.env.update(POLARS_MAX_THREADS='1')
    installed=e.install();assert installed.returncode==0,installed.stderr
    specpath=e.root/'data/kernels/rnx/kernel.json';spec=specpath.read_bytes();assert str(artifact).encode() in spec
    (O/'old-key-kernel.json').write_bytes(spec)
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    manager=KernelManager(kernel_name='rnx',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(e.root/'data/kernels')]))
    manager.start_kernel(env=e.env,cwd=str(e.notebooks));client=manager.client();client.start_channels();client.wait_for_ready(timeout=30);kernel_pid=manager.provisioner.pid;session_pid=t.p.pid
    def execute(source):
        mid=client.execute(source);outputs=[]
        while True:
            msg=client.get_iopub_msg(timeout=30)
            if msg.get('parent_header',{}).get('msg_id')!=mid:continue
            if msg['header']['msg_type'] in ['stream','execute_result','error']:outputs.append(msg['content'])
            if msg['header']['msg_type']=='status' and msg['content']['execution_state']=='idle':break
        while True:
            reply=client.get_shell_msg(timeout=30)
            if reply.get('parent_header',{}).get('msg_id')==mid:break
        assert reply['content']['status']=='ok',(source,outputs,reply)
        return outputs
    assert 'before' in str(execute('println!("{}",keep::read()); polars::lit(1).is_ok()'))
    # Readers do not own the cache writer lock. Inspection also works while the
    # fixture holds the writer locks, proving it cannot reserve deletion.
    records=[]
    for iteration in range(2):
        marker=f'live inspection {iteration}';retained.write_text(marker)
        cb=snap(cache);rb=snap(store,True);pb=snap(Path(d['old_manifest']).parent,True)
        with (cache/'locks'/f'{key}.lock').open('r+') as cl,(store/'install.lock').open('r+') as rl:
            fcntl.flock(cl,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(rl,fcntl.LOCK_EX|fcntl.LOCK_NB)
            for kind,root,which in [('cache',cache,key),('runtime',store,d['old_id'])]:
                for args in [[kind,'list','--root',root],[kind,'remove',which,'--root',root,'--dry-run']]:
                    p=call([P,*args]);records.append(json.loads(p.stdout))
        assert snap(cache)==cb and snap(store,True)==rb and snap(Path(d['old_manifest']).parent,True)==pb
        assert '42' in t.send('held') and marker in t.send('keep::read()')
        values=execute('println!("{}",keep::read()); polars::lit(1).is_ok()');assert marker in str(values) and 'true' in str(values)
        assert specpath.read_bytes()==spec
    results['live_inspection']={'session_pid':session_pid,'kernel_pid':kernel_pid,'rounds':2,'writer_locks_free_with_readers':True,'inspection_succeeds_with_writer_locks_held':True,'cache_metadata_unchanged':True,'runtime_bytes_unchanged':True,'project_bytes_unchanged':True,'kernelspec_unchanged':True,'reports':records}
    print('PASS live old session and kernel through inspection',flush=True)
    # Explicit stop, wait and reap, before any actual removal.
    client.stop_channels();client=None;manager.shutdown_kernel(now=False);manager.cleanup_resources();manager=None
    os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=10)==0
    assert not Path('/proc',str(kernel_pid)).exists() and not Path('/proc',str(session_pid)).exists()
    (O/'old-session.pty').write_bytes(t.log)
    keep=snap(cache/'entries'/newkey);selection=(store/'current.json').read_bytes();new_before=snap(new,True);projects=[Path(d['old_manifest']).parent,project];project_before=[snap(p,True) for p in projects]
    lock_inodes=[(cache/'locks'/f'{key}.lock').stat().st_ino,(store/'install.lock').stat().st_ino]
    removed=[]
    for kind,root,which in [('cache',cache,key),('runtime',store,d['old_id'])]:
        p=call([P,kind,'remove',which,'--root',root,'--quiescent']);removed.append([json.loads(v) for v in p.stdout.splitlines()]);assert not (root/'entries'/which).exists() and not (root/'removing'/which).exists()
    assert not retained.exists()
    assert snap(cache/'entries'/newkey)==keep and snap(new,True)==new_before and (store/'current.json').read_bytes()==selection
    assert [snap(p,True) for p in projects]==project_before and specpath.read_bytes()==spec
    assert [(cache/'locks'/f'{key}.lock').stat().st_ino,(store/'install.lock').stat().st_ino]==lock_inodes
    assert call([T,'eval','--manifest',manifest,'--','polars::lit(1).is_ok()']).stdout=='true\n'
    results['removal']={'consumers_reaped_before_removal':True,'reports':removed,'current_entry_unchanged':True,'selection_unchanged':True,'current_runtime_unchanged':True,'projects_and_kernelspec_unchanged':True,'locks_preserved':True,'new_polars_eval':True}
    (O/'journey.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS actual old entries removed after reaping; current entries work',flush=True)
finally:
    if client:client.stop_channels()
    if manager:
        if manager.has_kernel:manager.shutdown_kernel(now=False)
        manager.cleanup_resources()
    if e:e.close()
    if t:t.close()
