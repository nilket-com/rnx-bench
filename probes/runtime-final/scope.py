"""Default graph/public source boundary and real tool integrations."""
from pathlib import Path
import hashlib,io,json,subprocess as sp,tarfile,os
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/runtime-final-0064/scope';D=H/'target/before';BASE='1ecc35c'
D.mkdir(parents=True,exist_ok=True);O.mkdir(parents=True,exist_ok=True)
archive=sp.check_output(['git','-C',R,'archive',BASE,'Cargo.toml','Cargo.lock','src'])
with tarfile.open(fileobj=io.BytesIO(archive)) as t:t.extractall(D,filter='data')
trees={}
for name,root in [('before',D),('after',R)]:
 trees[name]=sp.check_output(['cargo','tree','--locked','--offline','--manifest-path',root/'Cargo.toml'],text=True).replace(str(root),'<RNX>')
 (O/('default-tree-'+name+'.txt')).write_text(trees[name])
assert trees['before']==trees['after']
protected=['src','Cargo.toml','Cargo.lock','THIRD-PARTY-NOTICES.md','jupyter','adapters','servers','tools/project/Cargo.toml','tools/project/Cargo.lock','tools/project/THIRD-PARTY-NOTICES.md']
assert not sp.check_output(['git','-C',R,'diff',BASE,'--',*protected])
assert 'polars' not in trees['after'] and 'tokio-postgres' not in trees['after']
meta=json.loads(sp.check_output(['cargo','metadata','--locked','--offline','--no-deps','--format-version','1'],cwd=R,text=True));assert len(meta['workspace_members'])==1
# Generated docs, as well as identical public source declarations.
with (O/'public-docs.log').open('w') as f:sp.run(['cargo','doc','--locked','--offline','--no-deps','--features','server-runtime,project-sources','--lib'],cwd=R,stdout=f,stderr=sp.STDOUT,check=True)
doc=R/'target/doc/rnx/all.html';assert doc.is_file()
import re
names=sorted(set(re.findall(r'href="([^"]+)"',doc.read_text())))
public=[n for n in names if n.startswith(('struct.','fn.','server/'))]
expected=sorted(['fn.main_with.html','server/struct.Invocation.html','server/struct.Program.html','server/struct.Failure.html','struct.Extensions.html','struct.Scope.html'])
assert public==expected,public
(O/'public-items.html').write_bytes(doc.read_bytes())
(O/'scope.json').write_text(json.dumps(dict(baseline=BASE,protected_paths=protected,protected_diff_empty=True,default_graph_equal=True,public_items=public,windows='type-check only; cfg(not(unix)) runtime CLI/discovery/validation return explicit unsupported errors; ordinary root session source unchanged'),indent=2)+'\n')
# Exercise ignored real handoff and native inventory checks against current product.
env=dict(os.environ,RNX_GATE2_BINARY=str(R/'target/debug/rnx'),RNX_GATE3_REPO=str(R),RNX_GATE3_INVENTORY=str(O/'native-inventory.json'))
rows=[]
for name,args in [('source-feature',['cargo','build','--locked','--offline','--features','project-sources','--bin','rnx']),('integrations',['cargo','test','--locked','--offline','--manifest-path','tools/project/Cargo.toml','--features','test-support','--','--ignored','--test-threads=1','--nocapture'])]:
 with (O/(name+'.log')).open('w') as f:p=sp.run(args,cwd=R,env=env,stdout=f,stderr=sp.STDOUT,timeout=600)
 rows.append(dict(name=name,command=args,status=p.returncode));(O/'integrations.json').write_text(json.dumps(rows,indent=2)+'\n');assert p.returncode==0,name
print('PASS protected scope, graph, public API and real integrations',flush=True)
