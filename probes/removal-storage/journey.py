"""Actual old/current storage; live retained-output consumers stop before deletion."""
from pathlib import Path
import os, sys, json, subprocess as sp, importlib.util, time, hashlib, fcntl, stat, shutil, selectors, signal, select, re

H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target/real';O=Path(os.environ.get('RNX_REMOVAL_RESULTS',str(B/'results/removal-storage-0066'))).resolve();O.mkdir(parents=True,exist_ok=True)
E=json.loads((W/'env.json').read_text());d=json.loads((W/'setup.json').read_text())
T=Path(d['tool']);P=W/'bin/rnx-project-support';store=Path(d['store'])
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
# Exercise current installed-default :dep, with no override, in the same cache.
# Only the old-key entry exists initially; both new-format assemblies must build.
nw=W/'current';nw.mkdir();(nw/'bin').mkdir();shutil.copy2(T,nw/'bin/rnx-project');shutil.copy2(Path(d['launcher']),nw/'bin/rnx')
env=dict(E,RNX_PROJECT_TOOL=str(nw/'bin/rnx-project'),XDG_STATE_HOME=str(nw/"state ' private"));env.pop('RNX_DEP_RUNTIME',None)
(nw/'env.json').write_text(json.dumps(env))
base=B/'probes/session-dogfood/check.py';raw=base.read_text()
raw=raw.replace("R=B.parent/'rnx'",'R=Path('+repr(str(new/'source'))+')')
raw=raw.replace("assert not (W/'cache/entries').exists(), 'cold control requires a fresh target/cache'", "assert {p.name for p in Path(ENV['RNX_PROJECT_CACHE']).joinpath('entries').iterdir()} == {"+repr(key)+"}, 'only old key may exist before the new cold builds'")
needle="assert 'bindings and declarations will be lost' in notice"
raw=raw.replace(needle,needle+'\n if "New scratch project:" in notice: assert '+repr('Runtime: installation '+newid)+' in notice')
script=O/'effective-dogfood.py';script.write_text(raw)
runner=nw/'run.py';runner.write_text('from pathlib import Path\np=Path('+repr(str(base))+')\ns=Path('+repr(str(script))+').read_text()\nexec(compile(s,str(p),"exec"),{"__file__":str(p),"__name__":"__main__"})\n')
with (O/'dogfood.log').open('w') as f:p=sp.run([sys.executable,runner],env=dict(env,RNX_DOGFOOD_TARGET=str(nw),RNX_DOGFOOD_RESULTS=str(O/'dogfood')),stdout=f,stderr=sp.STDOUT)
assert p.returncode==0,(O/'dogfood.log').read_text()
results['default_journeys']=json.loads((O/'dogfood/matrix.json').read_text())
project=nw/'absolute-project';manifest=project/'rnx.toml';rec=json.loads((project/'.rnx/receipt.json').read_text());newkey=rec['assembly_key'];assert newkey!=key
results['current_build']={'key':newkey,'receipt_format':rec['format'],'both_adapters':True}
print('PASS installed default :dep and typed query with current assemblies alongside old key',flush=True)

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
                    args += ['--manifest',d['old_manifest'],'--manifest',manifest]
                    p=call([T,*args]);records.append(json.loads(p.stdout))
        assert snap(cache)==cb and snap(store,True)==rb and snap(Path(d['old_manifest']).parent,True)==pb
        assert '42' in t.send('held') and marker in t.send('keep::read()')
        values=execute('println!("{}",keep::read()); polars::lit(1).is_ok()');assert marker in str(values) and 'true' in str(values)
        assert specpath.read_bytes()==spec
    results['live_inspection']={'session_pid':session_pid,'kernel_pid':kernel_pid,'rounds':2,'writer_locks_free_with_readers':True,'inspection_succeeds_with_writer_locks_held':True,'cache_metadata_unchanged':True,'runtime_bytes_unchanged':True,'project_bytes_unchanged':True,'kernelspec_unchanged':True,'reports':records}
    (O/'journey-progress.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS live old session and kernel through inspection',flush=True)
    # Explicit stop, wait and reap, before any actual removal.
    client.stop_channels();client=None;manager.shutdown_kernel(now=False);manager.cleanup_resources();manager=None
    os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=10)==0
    assert not Path('/proc',str(kernel_pid)).exists() and not Path('/proc',str(session_pid)).exists()
    (O/'old-session.pty').write_bytes(t.log)
    keep={p.name:snap(p,True) for p in (cache/'entries').iterdir() if p.name!=key};selection=(store/'current.json').read_bytes();new_before=snap(new,True);projects=[Path(d['old_manifest']).parent,project,nw/'relative-project',*[p.parent for p in Path(env['XDG_STATE_HOME']).rglob('rnx.toml')]];project_before=[snap(p,True) for p in projects]
    lock_inodes=[(cache/'locks'/f'{key}.lock').stat().st_ino,(store/'install.lock').stat().st_ino]
    removed=[]
    for kind,root,which in [('cache',cache,key),('runtime',store,d['old_id'])]:
        if kind=='cache':
            size=sum(q.stat().st_size for q in cache_entry.rglob('*') if q.is_file());assert size>500_000_000
            child=sp.Popen(list(map(str,[P,kind,'remove',which,'--root',root,'--quiescent'])),env=dict(E,RNX_REMOVE_PAUSE='during-delete',RNX_REMOVE_RELEASE=str(W/'release')),stdout=sp.PIPE,stderr=sp.PIPE)
            sel=selectors.DefaultSelector();sel.register(child.stdout,selectors.EVENT_READ);buf=b'';events=[];paused=False
            try:
                end=time.monotonic()+30
                while time.monotonic()<end and not paused:
                    if not sel.select(.1):assert child.poll() is None;continue
                    chunk=os.read(child.stdout.fileno(),65536);assert chunk;buf+=chunk
                    while b'\n' in buf:
                        line,buf=buf.split(b'\n',1);v=json.loads(line);events.append(v)
                        if v.get('paused')=='during-delete':paused=True
                assert paused and not cache_entry.exists() and (cache/'removing'/key).exists()
                child.kill();child.communicate(timeout=10);assert child.returncode==-signal.SIGKILL
            finally:
                if child.poll() is None:child.kill()
                child.wait(timeout=10);sel.close()
            command=next(v['resume_command'] for v in events if v.get('committed'))
            pending=call([P,'cache','remove',key,'--root',cache,'--resume','--dry-run']);assert json.loads(pending.stdout)['entries'][0]['location']=='removing'
            p=call(['/bin/sh','-c',command]);results['polars_interruption']={'logical_before':size,'killed_during_unlink':True,'resume_command':command,'events':events}
        else:p=call([T,kind,'remove',which,'--root',root,'--quiescent'])
        removed.append([json.loads(v) for v in p.stdout.splitlines()]);assert not (root/'entries'/which).exists() and not (root/'removing'/which).exists()
    assert not retained.exists()
    assert {p.name:snap(p,True) for p in (cache/'entries').iterdir()}==keep and snap(new,True)==new_before and (store/'current.json').read_bytes()==selection
    assert [snap(p,True) for p in projects]==project_before and specpath.read_bytes()==spec
    assert [(cache/'locks'/f'{key}.lock').stat().st_ino,(store/'install.lock').stat().st_ino]==lock_inodes
    assert call([T,'eval','--manifest',manifest,'--','polars::lit(1).is_ok()']).stdout=='true\n'
    results['removal']={'consumers_reaped_before_removal':True,'reports':removed,'current_entry_unchanged':True,'selection_unchanged':True,'current_runtime_unchanged':True,'projects_and_kernelspec_unchanged':True,'locks_preserved':True,'new_polars_eval':True}
    (O/'journey-progress.json').write_text(json.dumps(results,indent=2)+'\n')
    # Corruption is deletable owned data, not an authentication/repair path.
    badid='e'*64;bad=store/'entries'/badid;assert not bad.exists();shutil.copytree(new,bad)
    blob=next(q for q in (bad/'source/.git/objects').glob('*/*') if q.is_file());blob.chmod(0o600);blob.write_bytes(blob.read_bytes()+b'corruption')
    call([T,'runtime','remove',badid,'--root',store,'--quiescent']);assert not bad.exists() and (store/'current.json').read_bytes()==selection
    results['corrupt_runtime_removed_without_authentication']=True
    # Deliberately removing a current entry makes launch refuse without compilation.
    call([T,'cache','remove',newkey,'--root',cache,'--quiescent'])
    trace=O/'missing-launch.exec';p=call(['strace','-f','-qq','-e','trace=execve','-o',trace,T,'eval','--manifest',manifest,'--','42'],False)
    text=trace.read_text();programs=[Path(v).name for v in re.findall(r'execve\("([^"]+)"',text)];assert '--crate-name' not in text and not {'cargo','rustc'} & set(programs),text
    start=time.monotonic();p=call([T,'build','--offline','--manifest',manifest]);(O/'recovery-build.log').write_text(p.stdout+p.stderr)
    assert json.loads((project/'.rnx/receipt.json').read_text())['assembly_key']==newkey
    assert call([T,'eval','--manifest',manifest,'--','polars::lit(1).is_ok()']).stdout=='true\n'
    assert (store/'current.json').read_bytes()==selection and snap(new,True)==new_before and specpath.read_bytes()==spec
    results['explicit_rebuild']={'launch_execs':programs,'same_key':True,'seconds':time.monotonic()-start,'missing_launch_no_cargo':True,'polars_live':True}
    # The kept selected runtime still serves a fresh stock :dep after maintenance.
    Cluster=load('cluster',B/'probes/postgres/cluster.py').Cluster
    def until(terminal,needle,timeout=60):
        text='';end=time.monotonic()+timeout
        while time.monotonic()<end:
            if select.select([terminal.master],[],[],.1)[0]:
                chunk=os.read(terminal.master,65536);terminal.log+=chunk;text+=term.text(chunk)
                if needle in text:return text
        raise AssertionError((needle,text))
    with Cluster() as cluster:
        fresh=term.Terminal([Path(d['launcher']),'--no-splash','--color=never'],W,E)
        try:
            fresh.read();os.write(fresh.master,b':dep --offline polars postgres\n');notice=until(fresh,'Continue? [y/N]');assert 'Runtime: installation '+newid in notice
            os.write(fresh.master,b'y\n');out=until(fresh,'[1] >');assert 'restart is beginning' in out
            assert Path('/proc',str(fresh.p.pid),'exe').resolve().parent.parent.name==newkey
            assert 'true' in fresh.send('polars::lit(1).is_ok()')
            expression='let rows = postgres::query('+json.dumps(cluster.url)+', "SELECT $1::int8 AS n", [42], #{}).await.unwrap();'
            assert 'error at input' not in fresh.send(expression)
            assert 'error' not in fresh.send('assert!(rows.rows[0].n == 42);').lower()
            os.write(fresh.master,b':q\n');fresh.read(False);assert fresh.p.wait(timeout=10)==0
            cluster.wait_idle();results['post_removal_default']={'same_combined_key':True,'polars':True,'typed_query':True,'pid':fresh.p.pid}
            (O/'post-removal.pty').write_bytes(fresh.log)
        finally:fresh.close()
        postmaster=cluster.postmaster
    assert not Path('/proc',str(postmaster)).exists()
    assert (store/'current.json').read_bytes()==selection and snap(new,True)==new_before
    (O/'journey.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS actual old entries removed after reaping; current entries work',flush=True)
finally:
    if client:client.stop_channels()
    if manager:
        if manager.has_kernel:manager.shutdown_kernel(now=False)
        manager.cleanup_resources()
    if e:e.close()
    if t:t.close()
