#!/usr/bin/env python3
"""Build the standalone package, record its graph and exact fixture executables."""
import hashlib,json,pathlib,subprocess
HERE=pathlib.Path(__file__).resolve().parent
BENCH=HERE.parents[1];ROOT=BENCH.parent/'rnx';PACKAGE=ROOT/'servers/http-postgres'
def cargo(*args):
    return subprocess.check_output(['cargo',*args],cwd=PACKAGE,text=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
commands=[['build','--locked','--offline','--release','--features','test-support'],
          ['build','--locked','--offline','--release','--target-dir','target/plain']]
for args in commands:cargo(*args)
meta=json.loads(cargo('metadata','--locked','--offline','--format-version','1'))
graph={'scope':'Cargo resolved graph including platform/build/proc-macro packages; not a linker inventory',
       'packages':[{k:p[k] for k in ['name','version','license','source']} for p in meta['packages']],
       'resolve':meta['resolve']}
(PACKAGE/'dependency-graph.json').write_text(json.dumps(graph,indent=2).replace(str(ROOT),'<rnx>')+'\n')
subprocess.run(['python3','scripts/third-party-notices.py','--check'],cwd=PACKAGE,check=True)
binaries={name:{'path':str(path),'sha256':sha(path),'bytes':path.stat().st_size}
          for name,path in [('test-support',PACKAGE/'target/release/rnx-http-postgres'),('default',PACKAGE/'target/plain/release/rnx-http-postgres')]}
files=[PACKAGE/'Cargo.toml',PACKAGE/'Cargo.lock',PACKAGE/'dependency-graph.json',PACKAGE/'THIRD-PARTY-NOTICES.md',*sorted((PACKAGE/'src').glob('*.rs')),*sorted((PACKAGE/'examples').glob('*.rn'))]
conditions={'root_base':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'bench_base':subprocess.check_output(['git','rev-parse','HEAD'],cwd=BENCH,text=True).strip(),
            'commands':commands,'binaries':binaries,'files':{str(p.relative_to(PACKAGE)):sha(p) for p in files},
            'rustc':cargo('--version')+'\n'+subprocess.check_output(['rustc','-Vv'],text=True),
            'root_unchanged_files':{p:sha(ROOT/p) for p in ['Cargo.toml','Cargo.lock','THIRD-PARTY-NOTICES.md']}}
(HERE/'build.json').write_text(json.dumps(conditions,indent=2)+'\n')
print(json.dumps(binaries,indent=2))
