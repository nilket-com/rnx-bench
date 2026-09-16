#!/usr/bin/env python3
"""Deterministic generated Cargo wrapper and explicit executable hash override.
The input is hard-coded probe data, deliberately not a project manifest syntax.
"""
import hashlib,json,os,pathlib,shutil,subprocess,sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1];ROOT=BENCH.parent/'rnx';OUT=BENCH/'results/package-boundary/native';OUT.mkdir(parents=True,exist_ok=True)
WORK=HERE/'target/native';WORK.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(HERE.parent/'postgres'))
from cluster import Cluster

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(args,**kwargs):return subprocess.run(list(map(str,args)),check=True,**kwargs)
local=WORK/'local';(local/'src').mkdir(parents=True,exist_ok=True)
local_manifest='[package]\nname="local-fixture"\nversion="0.0.0"\nedition="2024"\npublish=false\n[workspace]\n[dependencies]\nrnx={path='+json.dumps(os.path.relpath(ROOT,local))+'}\n'
(local/'Cargo.toml').write_text(local_manifest)
local_source='pub fn build(m: &mut rnx::rune::Module) -> Result<Vec<(String, &\'static str)>, String> { m.function("answer", || 2i64).build().map_err(|e| e.to_string())?; Ok(vec![]) }\n'
(local/'src/lib.rs').write_text(local_source)
declarations=[{'module':'postgres','package':'rnx-postgres','path':ROOT/'adapters/postgres','hook':'with_lifecycle'}, {'module':'local','package':'local-fixture','path':local,'hook':'with'}]
def generate(directory,decls):
    (directory/'src').mkdir(parents=True,exist_ok=True)
    manifest='[package]\nname="assembled-probe"\nversion="0.0.0"\nedition="2024"\npublish=false\n[workspace]\n[dependencies]\nrnx={path='+json.dumps(os.path.relpath(ROOT,directory))+'}\n'
    expression='rnx::Extensions::none()'
    for n,d in enumerate(sorted(decls,key=lambda d:d['module'])):
        alias=f'native_{n}'
        manifest+=alias+'={package='+json.dumps(d['package'])+',path='+json.dumps(os.path.relpath(d['path'],directory))+'}\n'
        expression+='.'+d['hook']+'('+json.dumps(d['module'])+f', {alias}::build)'
    main='fn main() -> Result<(), Box<dyn std::error::Error>> {\n    rnx::main_with('+expression+')\n}\n'
    (directory/'Cargo.toml').write_text(manifest);(directory/'src/main.rs').write_text(main)
    return manifest,main
app=WORK/'generated-a';twin=WORK/'generated-b'
first=generate(app,declarations);second=generate(twin,list(reversed(declarations)));assert first==second
# Seed the accepted driver resolution. Cargo only adds the two local packages.
shutil.copyfile(ROOT/'adapters/postgres/Cargo.lock',app/'Cargo.lock')
env={k:v for k,v in os.environ.items() if k not in ('CARGO_TARGET_DIR','RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS')}
def build(locked=True):
    command=['cargo','build','--offline','--release','--manifest-path',app/'Cargo.toml']+(['--locked'] if locked else [])
    run(command,env=env,stdout=subprocess.DEVNULL)
build(False);lock=(app/'Cargo.lock').read_bytes();build();assert (app/'Cargo.lock').read_bytes()==lock
binary=app/'target/release/assembled-probe';original=sha(binary)
shutil.copyfile(app/'Cargo.lock',twin/'Cargo.lock')
run(['cargo','metadata','--locked','--offline','--no-deps','--format-version','1','--manifest-path',twin/'Cargo.toml'],env=env,stdout=subprocess.DEVNULL)
shutil.copyfile(app/'Cargo.lock',OUT/'Cargo.lock')
(OUT/'Cargo.toml.txt').write_text(first[0]);(OUT/'main.rs.txt').write_text(first[1]);(OUT/'local.rs.txt').write_text(local_source)
results={'generated_manifest_sha256':sha(app/'Cargo.toml'),'generated_main_sha256':sha(app/'src/main.rs'),'cargo_lock_sha256':sha(app/'Cargo.lock'),'reordered_input_byte_identical':True,'second_location_locked_metadata':True,'generated_binary_sha256':original,'local_manifest':local_manifest}
# Cargo.lock does not fingerprint local sources. This is a demonstration of
# why a future project lock must add source identity, not an accepted mutation.
before_source=sha(local/'src/lib.rs');(local/'src/lib.rs').write_text(local_source.replace('2i64','3i64'));build()
changed=sha(binary);assert changed!=original and (app/'Cargo.lock').read_bytes()==lock
p=run([binary,'eval','local::answer()'],capture_output=True,text=True,env=env);assert p.stdout.strip()=='3'
results['local_change']={'old_source':before_source,'new_source':sha(local/'src/lib.rs'),'new_binary':changed,'cargo_lock_unchanged':True,'answer':p.stdout.strip()}
(local/'src/lib.rs').write_text(local_source);build();assert sha(binary)==original
# Explicit path override uses the already assembled PostgreSQL executable.
prebuilt=ROOT/'adapters/postgres/target/release/rnx-pg';expected=sha(prebuilt)
copy=WORK/'prebuilt';shutil.copy2(prebuilt,copy)
def checked_path(path,digest):
    if sha(path)!=digest:raise ValueError('executable hash mismatch')
    return path
checked_path(copy,expected)
with copy.open('ab') as f:f.write(b'changed')
try:checked_path(copy,expected);raise AssertionError('hash mismatch accepted')
except ValueError:pass
shutil.copy2(prebuilt,copy);checked_path(copy,expected)
with Cluster() as c:
    child_env={k:v for k,v in env.items() if not k.startswith('RNX_')};child_env.update(TERM='xterm',NO_COLOR='1',RNX_CONFIG=str(c.root/'absent'),RNX_HISTORY=str(c.root/'history'))
    query='match postgres::query('+json.dumps(c.url)+', "SELECT $1::int8 AS n", [40], #{}).await { Ok(r) => r.rows[0].n + local::answer(), Err(e) => panic!("{}", e) }'
    file=c.root/'main.rn';file.write_text('pub async fn main(_) { '+query+' }')
    for mode,args,input in [('run',['run',str(file)],None),('eval',['eval',query],None),('session',[],query+'\n:reset\n'+query+'\n:q\n')]:
        p=run([binary,*args],input=input,env=child_env,text=True,capture_output=True,timeout=15)
        assert not p.stderr and p.stdout.count('42')==(2 if mode=='session' else 1),(mode,p.stdout,p.stderr)
        results[mode]=p.stdout
    p=run([checked_path(copy,expected),'eval',query.replace(' + local::answer()','')],env=child_env,text=True,capture_output=True,timeout=15)
    assert p.stdout.strip()=='40' and not p.stderr
    results['override']={'path':str(prebuilt),'sha256':expected,'query_value':p.stdout.strip(),'tampered_copy_refused_before_launch':True}
    # Reuse the accepted kernel fixture, replacing only the worker executable.
    os.environ['RNX_NOTEBOOK_RESULTS']=str(OUT/'notebook')
    sys.path.insert(0,str(HERE.parent/'jupyter-notebook'))
    from common import Environment
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    e=Environment();manager=None;client=None
    try:
        shutil.copy2(binary,e.worker);installed=e.install();assert installed.returncode==0,installed.stderr
        manager=KernelManager(kernel_name='rnx',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(e.root/'data/kernels')]))
        manager.start_kernel(env=e.env,cwd=str(e.notebooks));client=manager.client();client.start_channels();client.wait_for_ready(timeout=15)
        def cell(source):
            request=client.execute(source);outputs=[]
            while True:
                m=client.get_iopub_msg(timeout=15)
                if m.get('parent_header',{}).get('msg_id')!=request:continue
                if m['header']['msg_type']=='execute_result':outputs.append(m['content']['data']['text/plain'])
                if m['header']['msg_type']=='status' and m['content']['execution_state']=='idle':break
            reply=client.get_shell_msg(timeout=15);assert reply['parent_header']['msg_id']==request and reply['content']['status']=='ok',reply
            return outputs
        assert cell(query)==['42'];client.stop_channels();manager.restart_kernel(now=False)
        client=manager.client();client.start_channels();client.wait_for_ready(timeout=15);assert cell(query)==['42']
        results['notebook']={'query':42,'query_after_restart':42}
    finally:
        if client:client.stop_channels()
        if manager:
            if manager.has_kernel:manager.shutdown_kernel(now=False)
            manager.cleanup_resources()
        e.close()
    c.wait_idle();results['postmaster']=c.postmaster
results['postmaster_reaped']=not pathlib.Path('/proc',str(results['postmaster'])).exists()
assert results['postmaster_reaped']
(OUT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print('PASS deterministic wrapper, Cargo local-source counterexample, run/eval/session/notebook, executable override')
