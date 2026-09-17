"""Compare the default graph with the published pre-cache root, without a worktree."""
from pathlib import Path
import hashlib,io,json,subprocess,tarfile
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/adapter-commands-0062/regression';D=H/'target/before'
D.mkdir(parents=True,exist_ok=True)
base='075e95e'
archive=subprocess.check_output(['git','-C',R,'archive',base,'Cargo.toml','Cargo.lock','src'])
with tarfile.open(fileobj=io.BytesIO(archive)) as t:t.extractall(D,filter='data')
trees={}
for name,root in [('before',D),('after',R)]:
 trees[name]=subprocess.check_output(['cargo','tree','--locked','--offline','--manifest-path',str(root/'Cargo.toml')],text=True).replace(str(root),'<RNX>')
 (O/('default-tree-'+name+'.txt')).write_text(trees[name])
assert trees['before']==trees['after']
paths=subprocess.check_output(['git','-C',R,'diff','--name-only',base],text=True).splitlines()
assert all(p.startswith(('plans/','tools/project/')) for p in paths),paths
protected=['src','Cargo.toml','Cargo.lock','THIRD-PARTY-NOTICES.md','jupyter','adapters','servers','tools/project/Cargo.toml','tools/project/Cargo.lock','tools/project/THIRD-PARTY-NOTICES.md']
diff=subprocess.check_output(['git','-C',R,'diff',base,'--',*protected])
assert not diff,diff
metadata=json.loads(subprocess.check_output(['cargo','metadata','--locked','--offline','--no-deps','--format-version','1'],cwd=R,text=True))
assert len(metadata['workspace_members'])==1
result={'baseline':base,'head':subprocess.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip(),'changed_paths':paths,'protected_paths':protected,'protected_diff_empty':True,'default_tree_equal':True,'tree_sha256':hashlib.sha256(trees['after'].encode()).hexdigest(),'workspace_members':metadata['workspace_members']}
(O/'scope.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS root/default graph and independent packages unchanged since gate 1',flush=True)
