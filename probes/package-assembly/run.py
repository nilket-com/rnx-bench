#!/usr/bin/env python3
"""0057 gate 4: exercise private Rust assembly primitives, not a product CLI."""
import hashlib,json,os,pathlib,shutil,signal,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent
BENCH=HERE.parents[1]; ROOT=BENCH.parent/'rnx'
OUT=BENCH/'results/package-assembly-0057';OUT.mkdir(parents=True,exist_ok=True)
WORK=HERE/'target';WORK.mkdir(exist_ok=True)
PROJECT=WORK/'project';PROJECT.mkdir(exist_ok=True)
STAGE=PROJECT/'.rnx/build';STAGE.parent.mkdir(exist_ok=True)
PROBE=ROOT/'tools/project/target/debug/rnx-project-assembly-probe'
# Reuse existing release objects, not a second compiler configuration.
CACHE=BENCH/'probes/package-boundary/target/native/generated-a/target'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','CARGO_')) and k not in ('RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER')}
ENV.update(TERM='xterm',NO_COLOR='1',RNX_CONFIG=str(WORK/'missing-config'),RNX_HISTORY=str(WORK/'history'))
def execute(args,**kwargs):return subprocess.run(list(map(str,args)),env=ENV,capture_output=True,text=True,timeout=kwargs.pop('timeout',30),**kwargs)
def success(args,**kwargs):
    p=execute(args,**kwargs);assert p.returncode==0,(args,p.returncode,p.stdout,p.stderr);return p
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,text):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
plain=WORK/'plain';write(plain/'Cargo.toml','[package]\nname="gate-four-plain"\nversion="0.0.0"\nedition="2024"\n[workspace]\n[dependencies]\nrnx={path='+json.dumps(str(ROOT))+'}\n')
write(plain/'src/lib.rs',"pub fn build(m: &mut rnx::rune::Module) -> Result<Vec<(String, &'static str)>, String> { m.function(\"answer\", || 2i64).build().map_err(|e| e.to_string())?; Ok(vec![]) }\n")
success(['git','init','--quiet',plain]);success(['git','-C',plain,'add','Cargo.toml','src/lib.rs'])
words=WORK/'words';write(words/'rnx.toml','format=1\n[source]\nroot="src"\n');write(words/'src/mod.rn','pub fn one() { 1 }\n')
manifest='format=1\n[application]\nentry="main.rn"\n[runtime]\npath='+json.dumps(str(ROOT))+'\n[sources.words]\npath="../words"\n[native.local]\npath="../plain"\npackage="gate-four-plain"\nbuilder="build"\nhook="plain"\n[native.postgres]\npath='+json.dumps(str(ROOT/'adapters/postgres'))+'\npackage="rnx-postgres"\nbuilder="build"\nhook="lifecycle"\n'
write(PROJECT/'rnx.toml',manifest);write(PROJECT/'main.rn','mod words; pub fn main(_) { words::one() + local::answer() }\n')
if STAGE.exists():shutil.rmtree(STAGE)
success([PROBE,'prepare',PROJECT/'rnx.toml',STAGE])
# Cargo owns resolution. Seed the accepted registry graph, allow local additions,
# then require locked build; lock/receipt publication itself is gate 5.
shutil.copyfile(ROOT/'adapters/postgres/Cargo.lock',STAGE/'Cargo.lock')
build_env=dict(ENV,CARGO_TARGET_DIR=str(CACHE))
with (OUT/'build.log').open('w') as log:
    for command in [['cargo','metadata','--offline','--format-version','1','--manifest-path',str(STAGE/'Cargo.toml')],['cargo','build','--release','--offline','--locked','--manifest-path',str(STAGE/'Cargo.toml')]]:
        p=subprocess.run(command,env=build_env,cwd=PROJECT,stdout=subprocess.PIPE,stderr=log,text=True,timeout=900)
        assert p.returncode==0,command
        if command[1]=='metadata':(OUT/'resolved-graph.json').write_text(p.stdout)
BINARY=CACHE/'release/rnx-project-app';HASH=success([PROBE,'hash',BINARY]).stdout.strip();assert HASH==sha(BINARY)
for name in ['Cargo.toml','Cargo.lock','src/main.rs','source-map.json']:
    shutil.copyfile(STAGE/name,OUT/(name.replace('/','-')+'.txt'))
(OUT/'project.toml.txt').write_text(manifest);(OUT/'plain.rs.txt').write_text((plain/'src/lib.rs').read_text())
MAP=STAGE/'source-map.json';ENTRY=PROJECT/'main.rn'
def launch(exe=BINARY,digest=HASH,mapping=MAP,entry=ENTRY,args=()):return [PROBE,'run',exe,digest,mapping if mapping else '-',entry,*args]
results={'binary':str(BINARY),'sha256':HASH,'locked_build':True,'scope':'assembly primitives; no product lock/receipt yet'}
assert success(launch()).stdout.strip()=='3'
sys.path.insert(0,str(HERE.parent/'postgres'));from cluster import Cluster
with Cluster() as c:
    payload="quotes ' ; SELECT 99; \\ emoji 🦀"
    source='mod words; pub async fn main(args) { let r=postgres::query('+json.dumps(c.url)+', "SELECT $1::text AS value, $2::int8 AS n", [args[0], 39], #{}).await?; [r.rows[0].value, r.rows[0].n + words::one() + local::answer(), args[1]] }\n'
    ENTRY.write_text(source)
    p=success(launch(args=[payload,'--color=never']),cwd='/tmp');assert not p.stderr and json.loads(p.stdout)==[payload,42,'--color=never'],p
    results['mapped_query_and_arguments']=json.loads(p.stdout)
    plain_entry=WORK/'plain.rn';plain_entry.write_text('pub async fn main(_) { postgres::query('+json.dumps(c.url)+', "SELECT $1::int8 AS n", [42], #{}).await?.rows[0].n }')
    old=ROOT/'adapters/postgres/target/release/rnx-pg';old_hash=success([PROBE,'hash',old]).stdout.strip()
    assert success(launch(old,old_hash,None,plain_entry)).stdout.strip()=='42'
    refused=execute(launch(old,old_hash,MAP));assert refused.returncode and not refused.stdout and 'capability' in refused.stderr,refused
    results['old_override']={'sha256':old_hash,'query':42,'mapped_refusal':refused.stderr}
    copy=WORK/'override';shutil.copy2(BINARY,copy)
    assert json.loads(success(launch(copy,HASH,MAP,args=[payload,'--color=never'])).stdout)==[payload,42,'--color=never']
    with copy.open('ab') as f:f.write(b'changed')
    refused=execute(launch(copy,HASH,MAP,args=[payload,'--color=never']));assert refused.returncode and not refused.stdout and 'hash mismatch' in refused.stderr
    results['source_capable_override_and_tamper_refusal']=True
    query='postgres::query('+json.dumps(c.url)+', "SELECT $1::int8 AS n", [40], #{}).await?.rows[0].n + local::answer()'
    assert success([BINARY,'eval',query]).stdout.strip()=='42'
    p=success([BINARY],input=query+'\n:reset\n'+query+'\nmod words;\n:q\n');assert p.stdout.count('42')==2 and 'modules' in p.stderr,(p.stdout,p.stderr)
    results['session_reset_and_module_refusal']={'stdout':p.stdout,'stderr':p.stderr}
    p=execute([BINARY,'eval','mod words;']);assert p.returncode and 'modules' in p.stderr
    # Same kernel installer and pinned client as the accepted native fixture.
    os.environ['RNX_NOTEBOOK_RESULTS']=str(OUT/'notebook')
    sys.path.insert(0,str(HERE.parent/'jupyter-notebook'))
    from common import Environment
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    e=Environment();manager=None;client=None;owned=set()
    def collect(pid):
        owned.add(pid)
        children=pathlib.Path(f'/proc/{pid}/task/{pid}/children')
        if children.exists():
            for child in children.read_text().split():collect(int(child))
    try:
        shutil.copy2(BINARY,e.worker);installed=e.install();assert installed.returncode==0,installed.stderr
        manager=KernelManager(kernel_name='rnx',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(e.root/'data/kernels')]))
        manager.start_kernel(env=e.env,cwd=str(e.notebooks));client=manager.client();client.start_channels();client.wait_for_ready(timeout=15);collect(manager.provisioner.pid)
        def cell(source):
            request=client.execute(source);outputs=[]
            while True:
                m=client.get_iopub_msg(timeout=15)
                if m.get('parent_header',{}).get('msg_id')!=request:continue
                if m['header']['msg_type'] in ['execute_result','error']:outputs.append(m['content'])
                if m['header']['msg_type']=='status' and m['content']['execution_state']=='idle':break
            while True:
                reply=client.get_shell_msg(timeout=15)
                if reply.get('parent_header',{}).get('msg_id')==request:break
            return reply['content'],outputs
        before,outputs=cell('let saved = 7; '+query);assert before['status']=='ok' and outputs[0]['data']['text/plain']=='42'
        missing,_=cell('mod words;');assert missing['status']=='error'
        client.stop_channels();manager.restart_kernel(now=False);client=manager.client();client.start_channels();client.wait_for_ready(timeout=15);collect(manager.provisioner.pid)
        after,outputs=cell(query);assert after['status']=='ok' and outputs[0]['data']['text/plain']=='42'
        missing,_=cell('saved');assert missing['status']=='error'
        results['notebook']={'before':before,'after':after,'binding_lost':missing,'modules_refused':True}
    finally:
        if client:client.stop_channels()
        if manager:
            if manager.has_kernel:manager.shutdown_kernel(now=False)
            manager.cleanup_resources()
        e.close()
    deadline=time.monotonic()+5
    while any(pathlib.Path('/proc',str(pid)).exists() for pid in owned):
        assert time.monotonic()<deadline,('notebook process survived',owned)
        time.sleep(.01)
    results['notebook']['owned_pids']=sorted(owned);results['notebook']['all_reaped']=True
    c.wait_idle();results['postmaster']=c.postmaster
assert not pathlib.Path('/proc',str(results['postmaster'])).exists()
# Exit statuses pass through the Unix exec-based launcher.
ENTRY.write_text('pub fn main(_) { process::exit(7); }')
p=execute(launch());assert p.returncode==7,(p.returncode,p.stdout,p.stderr);results['exit_status']=7
pidfile=WORK/'child.pid';pidfile.unlink(missing_ok=True)
child_code='import os,time,pathlib; pathlib.Path('+repr(str(pidfile))+').write_text(str(os.getpid())); time.sleep(60)'
ENTRY.write_text('pub async fn main(_) { let reply=process::run("python3", ["-c", '+json.dumps(child_code)+'], #{}).unwrap(); time::sleep(10000).await?; reply }')
p=subprocess.Popen(list(map(str,launch())),env=ENV,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
child=None
try:
    deadline=time.monotonic()+10
    while not pidfile.exists():
        assert p.poll() is None, p.communicate()
        assert time.monotonic()<deadline,'child never started'
        time.sleep(.01)
    child=int(pidfile.read_text());os.kill(p.pid,signal.SIGINT);stdout,stderr=p.communicate(timeout=10)
    assert p.returncode==130,(p.returncode,stdout,stderr)
    assert not pathlib.Path('/proc',str(child)).exists(),child
    results['interrupt']={'status':p.returncode,'child_reaped':True,'stdout':stdout,'stderr':stderr}
finally:
    if p.poll() is None:os.killpg(p.pid,signal.SIGKILL);p.communicate()
    if child and pathlib.Path('/proc',str(child)).exists():os.kill(child,signal.SIGKILL)
results['postmaster_reaped']=True
(OUT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print('PASS gate 4: generated build, mapped query, arguments, status, interrupt, overrides, session and notebook restart')
