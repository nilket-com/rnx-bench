#!/usr/bin/env python3
"""Black-box workflow failure gates, with a tiny API-compatible Cargo fixture."""
import hashlib,json,os,pathlib,shutil,signal,subprocess,tempfile,time
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1];ROOT=BENCH.parent/'rnx'
TOOL=pathlib.Path(os.environ.get('RNX_PROJECT_TOOL',str(ROOT/'tools/project/target/debug/rnx-project')))
OUT=BENCH/'results/cache-regression-0061/workflow';OUT.mkdir(parents=True,exist_ok=True)
ENV={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_'))}
results={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='rnx-project-workflow-') as tmp:
    root=pathlib.Path(tmp); app=root/'app';native=root/'runtime';app.mkdir();(native/'src').mkdir(parents=True)
    manifest=app/'rnx.toml';manifest.write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath="../runtime"\n')
    (app/'main.rn').write_text('pub fn main(_) {42}\n')
    cargo='[package]\nname="rnx"\nversion="0.0.0"\nedition="2024"\n[features]\nproject-sources=[]\n'
    (native/'Cargo.toml').write_text(cargo)
    source='pub struct Extensions; impl Extensions { pub fn none()->Self {Self} } pub fn main_with(_:Extensions)->Result<(),Box<dyn std::error::Error>>{ let a=std::env::args().collect::<Vec<_>>(); if a[1]=="project-source-version" {println!("{}", r#"{"format":1}"#);}else{println!("RAN:{}", a.last().unwrap());} Ok(()) }'
    (native/'src/lib.rs').write_text(source)
    for command in [['git','init','--quiet',native],['git','-C',native,'add','.']]:subprocess.run(list(map(str,command)),check=True)
    def command(op,extra=()):return [('/home/me/work/rnx-bench/probes/cache-commands/target/legacy-tool' if op=='lock' else str(TOOL)),op,'--manifest',str(manifest),*extra]
    def run(op,extra=(),ok=True,env=None):
        p=subprocess.run(command(op,extra),env=env or ENV,capture_output=True,text=True,timeout=60)
        assert (p.returncode==0)==ok,(op,p.returncode,p.stdout,p.stderr)
        return p
    run('lock',['--offline']);run('build',['--offline']);p=run('run',['--','sentinel']);assert p.stdout=='RAN:sentinel\n' and not p.stderr,p
    assert {p.name for p in app.iterdir()}=={'rnx.toml','main.rn','rnx.lock','rnx.Cargo.lock','.rnx'}
    subprocess.run(['git','init','--quiet',str(app)],check=True)
    visible=subprocess.check_output(['git','-C',str(app),'ls-files','--others','--exclude-standard'],text=True).splitlines()
    assert set(visible)=={'rnx.toml','main.rn','rnx.lock','rnx.Cargo.lock'},visible
    assert 'override' in run('lock',['--offline'],False,env=dict(ENV,RUSTFLAGS='--cfg forbidden')).stderr
    first_receipt=json.loads((app/'.rnx/receipt.json').read_text());first_binary=app/'.rnx/artifacts'/first_receipt['executable_sha256']
    capability=subprocess.run([str(first_binary),'project-source-version'],capture_output=True,text=True,check=True,env=ENV);assert json.loads(capability.stdout)=={'format':1}
    results['layout_and_success']=True
    pair=(sha(app/'rnx.lock'),sha(app/'rnx.Cargo.lock'))
    oldmanifest=manifest.read_text();manifest.write_text(oldmanifest+'unknown=1\n');run('lock',['--offline'],False);assert pair==(sha(app/'rnx.lock'),sha(app/'rnx.Cargo.lock'));manifest.write_text(oldmanifest)
    results['invalid_lock_retains_pair']=True
    # No Cargo (or rustc) may be invoked by run.
    fake=root/'bin';fake.mkdir();marker=root/'compiler-called'
    for name in ['cargo','rustc']:
        path=fake/name;path.write_text('#!/bin/sh\necho called > "'+str(marker)+'"\nexit 98\n');path.chmod(0o755)
    run('run',['--','no-cargo'],env=dict(ENV,PATH=str(fake)+os.pathsep+ENV['PATH']));assert not marker.exists();results['run_invokes_no_cargo_or_rustc']=True
    receipt=app/'.rnx/receipt.json';oldreceipt=receipt.read_bytes();receipt.write_text('{}');run('run',ok=False);receipt.write_bytes(oldreceipt)
    d=json.loads(receipt.read_text());artifact=app/'.rnx/artifacts'/d['executable_sha256'];original=artifact.read_bytes();artifact.write_bytes(original+b'tampered');p=run('run',ok=False);assert not p.stdout and 'hash mismatch' in p.stderr;artifact.write_bytes(original)
    results['receipt_and_binary_tamper']=True
    old=(app/'main.rn').read_text();(app/'main.rn').write_text(old+'// dirty\n');p=run('run',ok=False);assert 'changed' in p.stderr;run('build',['--offline'],False);assert not receipt.exists();(app/'main.rn').write_text(old);run('build',['--offline'])
    results['stale_inputs_refuse_without_build']=True
    # Compile errors name Cargo's real package; lock alone never compiles.
    (native/'src/lib.rs').write_text('this is not Rust');run('lock',['--offline']);p=run('build',['--offline'],False);assert 'rnx' in p.stderr and not receipt.exists();(native/'src/lib.rs').write_text(source);run('lock',['--offline']);run('build',['--offline']);results['failed_compile_no_receipt']=True
    def pause(op,name):
        marker=root/'pause';marker.unlink(missing_ok=True)
        p=subprocess.Popen(command(op,['--offline']),env=dict(ENV,RNX_PROJECT_PAUSE=name,RNX_PROJECT_PAUSE_FILE=str(marker)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        deadline=time.monotonic()+30
        while not marker.exists():
            assert p.poll() is None,p.communicate()
            assert time.monotonic()<deadline,'pause missing'
            time.sleep(.01)
        return p,marker
    p,marker=pause('build','after-build')
    try:
        assert 'active' in run('lock',['--offline'],False).stderr
        (app/'main.rn').write_text(old+'// edited during build\n');marker.unlink();stdout,stderr=p.communicate(timeout=10);assert p.returncode and 'changed' in stderr and not receipt.exists()
    finally:
        if p.poll() is None:p.kill();p.communicate()
    (app/'main.rn').write_text(old);results['concurrent_edit_and_writer_exclusion']=True
    p,marker=pause('build','after-build');os.kill(p.pid,signal.SIGINT);p.communicate(timeout=10);assert p.returncode==130 and not receipt.exists();marker.unlink();results['interrupted_build_no_receipt']=True
    p,marker=pause('build','after-build');os.kill(p.pid,signal.SIGTERM);p.communicate(timeout=10);assert p.returncode==143 and not receipt.exists();marker.unlink();results['terminated_build_no_receipt']=True
    # Change Cargo.lock itself so the interrupted publication is discriminating.
    oldlock=(app/'rnx.lock').read_bytes();(native/'Cargo.toml').write_text(cargo.replace('0.0.0','0.0.1'))
    oldcargo=(app/'rnx.Cargo.lock').read_bytes()
    p=run('lock',['--offline'],False,env=dict(ENV,RNX_PROJECT_FAIL='after-json-publication'))
    assert 'injected failure' in p.stderr and (app/'rnx.lock').read_bytes()==oldlock and (app/'rnx.Cargo.lock').read_bytes()==oldcargo
    results['normal_publication_failure_restores_both_files']=True
    p,marker=pause('lock','after-cargo-publication');os.kill(p.pid,signal.SIGINT);p.communicate(timeout=10);assert p.returncode==130 and (app/'rnx.lock').read_bytes()==oldlock
    assert 'pair mismatch' in run('run',ok=False).stderr;assert 'pair mismatch' in run('build',['--offline'],False).stderr;marker.unlink();run('lock',['--offline']);run('build',['--offline']);run('run');results['interrupted_pair_refused_then_explicit_relock']=True
    # A copied equivalent layout retains content digests, not absolute identities.
    clone=root/'clone';shutil.copytree(app,clone,ignore=shutil.ignore_patterns('.rnx','.git'));manifest=clone/'rnx.toml'
    assert 'changed' in run('run',ok=False).stderr
    before=json.loads((clone/'rnx.lock').read_text());run('lock',['--offline']);after=json.loads((clone/'rnx.lock').read_text());assert before['inputs']['source']['trees'][0]['sha256']==after['inputs']['source']['trees'][0]['sha256'];assert before!=after;results['copy_requires_relock_tree_digest_stable']=True
    # Interrupt an actual Cargo build with a build-script grandchild running.
    manifest=app/'rnx.toml'
    pids=root/'build-pids'
    build_source='fn main(){let child=std::process::Command::new("sleep").arg("60").spawn().unwrap(); std::fs::write('+json.dumps(str(pids))+',format!("{} {}",std::process::id(),child.id())).unwrap();std::thread::sleep(std::time::Duration::from_secs(60));}'
    (native/'build.rs').write_text(build_source)
    subprocess.run(['git','-C',str(native),'add','build.rs'],check=True)
    run('lock',['--offline'])
    child=subprocess.Popen(command('build',['--offline']),env=ENV,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        deadline=time.monotonic()+30
        while not pids.exists():
            assert child.poll() is None,child.communicate()
            assert time.monotonic()<deadline,'build script missing'
            time.sleep(.01)
        owned=list(map(int,pids.read_text().split()));os.kill(child.pid,signal.SIGINT);stdout,stderr=child.communicate(timeout=10)
        assert child.returncode==130 and not receipt.exists(),(child.returncode,stderr)
        deadline=time.monotonic()+5
        while any(pathlib.Path('/proc',str(pid)).exists() for pid in owned):
            assert time.monotonic()<deadline,('build descendant survived',owned)
            time.sleep(.01)
        results['cargo_interrupt_reaps_build_script_and_child']=True
    finally:
        if child.poll() is None:child.kill();child.communicate()
    manifest=clone/'rnx.toml'
    nested=native/'project';nested.mkdir();(nested/'main.rn').write_text('pub fn main(_) {42}');(nested/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath=".."\n')
    subprocess.run(['git','-C',str(native),'add','project'],check=True)
    manifest=nested/'rnx.toml';p=run('lock',['--offline'],False);assert 'self-referential' in p.stderr and not (nested/'rnx.lock').exists() and not (nested/'rnx.Cargo.lock').exists()
    results['self_referential_native_root_refused']=True
    manifest=clone/'rnx.toml'
    # Build overrides are forbidden; lock and run require neither Cargo nor receipt.
    override=root/'override';shutil.copy2(artifact,override)
    manifest.write_text('format=1\n[application]\nentry="main.rn"\n[executable]\npath="../override"\n')
    run('lock',env=dict(ENV,PATH=str(fake)+os.pathsep+ENV['PATH']));assert not (clone/'rnx.Cargo.lock').exists();run('run',env=dict(ENV,PATH=str(fake)+os.pathsep+ENV['PATH']));assert not marker.exists();run('build',ok=False);results['override_without_cargo_or_receipt']=True
    package=root/'source-package';package.mkdir();(package/'rnx.toml').write_text('format=1\n[source]\nroot=".."\n')
    manifest.write_text(manifest.read_text()+'[sources.parent]\npath="../source-package"\n');before=sha(clone/'rnx.lock');p=run('lock',ok=False);assert 'inside source root' in p.stderr and before==sha(clone/'rnx.lock')
    results['self_referential_source_root_refused']=True
(OUT/'workflow.json').write_text(json.dumps(results,indent=2)+'\n')
print('PASS',len(results),'workflow groups')
