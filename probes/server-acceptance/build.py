#!/usr/bin/env python3
"""Matched stock builds: fixed pre-0056 baseline and current root, no server deps."""
import hashlib,json,os,pathlib,shutil,subprocess
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1];ROOT=BENCH.parent/'rnx'
OUT=BENCH/'results/server-acceptance-0056';OUT.mkdir(parents=True,exist_ok=True)
WORK=HERE/'target';WORK.mkdir(exist_ok=True);BEFORE=WORK/'before-tree'
base=subprocess.check_output(['git','rev-parse','032579a'],cwd=ROOT,text=True).strip()
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
if BEFORE.exists():shutil.rmtree(BEFORE)
BEFORE.mkdir();subprocess.run(['tar','-x','-C',str(BEFORE)],input=subprocess.check_output(['git','archive',base],cwd=ROOT),check=True)
env={k:v for k,v in os.environ.items() if k not in ('CARGO_TARGET_DIR','RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS')}
def call(args,cwd):return subprocess.check_output(args,cwd=cwd,env=env,text=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
data={'before_commit':base,'after_commit':head,'rustc':call(['rustc','-Vv'],ROOT),'binaries':{},'graph':{},'commands':[]}
for name,tree,target in [('before',BEFORE,WORK/'before-build'),('after',ROOT,WORK/'after-build')]:
    command=['cargo','build','--locked','--offline','--release','--target-dir',str(target)]
    data['commands'].append({'cwd':str(tree),'args':command});call(command,tree)
    binary=target/'release/rnx';data['binaries'][name]={'path':str(binary),'sha256':sha(binary),'bytes':binary.stat().st_size}
    graph=call(['cargo','tree','--locked','--offline','--edges','normal,build','--prefix','none','--format','{p} {f}'],tree).replace(str(tree),'<rnx>')
    (OUT/(name+'-default-graph.txt')).write_text(graph);data['graph'][name]=hashlib.sha256(graph.encode()).hexdigest()
    data[name+'_lock_sha256']=sha(tree/'Cargo.lock')
assert data['graph']['before']==data['graph']['after']
assert data['before_lock_sha256']==data['after_lock_sha256']
isolated=call(['cargo','metadata','--locked','--offline','--no-deps','--format-version','1'],ROOT)
meta=json.loads(isolated);assert len(meta['workspace_members'])==1 and len(meta['packages'])==1 and meta['packages'][0]['name']=='rnx'
data['root_workspace_members']=meta['workspace_members']
(OUT/'build.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data['binaries'],indent=2))
