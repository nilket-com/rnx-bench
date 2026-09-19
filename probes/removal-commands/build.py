from pathlib import Path
import subprocess as sp,os,shutil,json,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/removal-commands-0066';W=H/'target';(W/'bin').mkdir(parents=True,exist_ok=True)
rows=[]
def run(name,args):
    with (O/(name+'.log')).open('w') as f:p=sp.run(list(map(str,args)),stdout=f,stderr=sp.STDOUT)
    assert p.returncode==0,(O/(name+'.log')).read_text();rows.append(dict(check=name,status=0));print('PASS',name,flush=True)
manifest=R/'tools/project/Cargo.toml'
run('fmt',['cargo','fmt','--manifest-path',manifest,'--','--check'])
for mode,features in [('ordinary',[]),('support',['--features','test-support'])]:
    run('clippy-'+mode,['cargo','clippy','--locked','--offline','--manifest-path',manifest,'--all-targets',*features,'--','-D','warnings'])
    run('test-'+mode,['cargo','test','--locked','--offline','--manifest-path',manifest,*features,'--','--test-threads=1'])
    run('build-'+mode,['cargo','build','--locked','--offline','--release','--manifest-path',manifest,'--bin','rnx-project',*features])
    shutil.copy2(R/'tools/project/target/release/rnx-project',W/'bin'/('rnx-project-'+mode))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files={str(p.relative_to(R)):sha(p) for p in (R/'tools/project/src').rglob('*.rs')}
# Reproducible source archive for every new/changed Rust file, not hashes alone.
baseline='bafa2a0';changed=sp.check_output(['git','-C',R,'diff','--name-only',baseline,'--','tools/project/src'],text=True).splitlines()
changed+=sp.check_output(['git','-C',R,'ls-files','--others','--exclude-standard','tools/project/src'],text=True).splitlines()
for name in sorted(set(changed)):
    dst=H/'source'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/name,dst)
for n in ['Cargo.toml','Cargo.lock']:
    assert (R/'tools/project'/n).read_bytes()==sp.check_output(['git','-C',R,'show',baseline+':tools/project/'+n])
(O/'build.json').write_text(json.dumps(dict(baseline=baseline,checks=rows,sources_sha256=files,binaries={n:sha(W/'bin'/('rnx-project-'+n)) for n in ['ordinary','support']},cargo_files_unchanged=True),indent=2)+'\n')
