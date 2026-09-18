#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess,sys
B=pathlib.Path(__file__).resolve().parents[2];R=B.parent/'rnx';OUT=B/'results/inventory-encoding-0065';OUT.mkdir(exist_ok=True)
base=['--offline','--locked','--manifest-path','tools/project/Cargo.toml']
commands=[('fmt',['cargo','fmt','--manifest-path','tools/project/Cargo.toml','--','--check'])]
for name,features in [('default',[]),('support',['--features','test-support'])]:
    commands += [('clippy-'+name,['cargo','clippy',*base,*features,'--all-targets','--','-D','warnings']),
                 ('tests-'+name,['cargo','test',*base,*features,'--','--test-threads=1'])]
commands += [('notices',[sys.executable,'tools/project/scripts/notices.py','--check']),
             ('probe-build',['cargo','build',*base,'--release','--features','test-support','--bin','rnx-project-assembly-probe'])]
results=[]
for name,args in commands:
    with (OUT/(name+'.log')).open('w') as f:
        p=subprocess.run(args,cwd=R,stdout=f,stderr=subprocess.STDOUT)
    results.append({'name':name,'args':args,'status':p.returncode})
    (OUT/'checks.json').write_text(json.dumps({'complete':False,'checks':results},indent=2)+'\n')
    assert p.returncode==0,(name,p.returncode)
    print(name,'passes',flush=True)
unchanged=subprocess.check_output(['git','diff','--name-only','601ce23','--','.',':(exclude)tools/project/**',':(exclude)plans/**'],cwd=R,text=True)
assert not unchanged,unchanged
oldwire=subprocess.check_output(['git','show','601ce23:tools/project/src/wire.rs'],cwd=R,text=True)
wire=(R/'tools/project/src/wire.rs').read_text()
assert oldwire.split('pub(crate) struct Lock')[0]==wire.split('pub(crate) struct Lock')[0]
oldmanifest=subprocess.check_output(['git','show','601ce23:tools/project/src/manifest.rs'],cwd=R)
assert oldmanifest==(R/'tools/project/src/manifest.rs').read_bytes()
metadata=json.loads(subprocess.check_output(['cargo','metadata',*base,'--format-version','1'],cwd=R))
blake=next(p for p in metadata['packages'] if p['name']=='blake3')
node=next(n for n in metadata['resolve']['nodes'] if n['id']==blake['id'])
assert not {'rayon','mmap'}.intersection(node['features'])
assert all(p['name'] not in ('rayon','rayon-core') for p in metadata['packages'])
original=subprocess.check_output(['git','show','7cd3205:tools/project/src/fingerprint.rs'],cwd=R,text=True)
legacy=(R/'tools/project/src/fingerprint/legacy.rs').read_text()
original=original[original.index('fn fail('):].replace('\n#[cfg(test)]\nmod tests;\n','').strip()
legacy=legacy[legacy.index('fn fail('):].replace('super::tests::after_open','tests::after_open').strip()
assert legacy==original,'legacy reader function bodies drifted'
(OUT/'checks.json').write_text(json.dumps({'complete':True,'checks':results,'blake3_features':node['features'],'root_unchanged_outside_tool_and_plan':True,'handoff_and_manifest_unchanged':True,'legacy_matches_v1_function_bodies':True},indent=2)+'\n')
paths=sorted((R/'tools/project/src').rglob('*.rs'))+sorted((R/'tools/project/src').rglob('*.json'))+[R/'tools/project/Cargo.toml',R/'tools/project/Cargo.lock']
(OUT/'source-digests.json').write_text(json.dumps({str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2)+'\n')
