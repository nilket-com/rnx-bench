#!/usr/bin/env python3
"""Fixture generation is explicit probe input, not a proposed project manifest."""
import hashlib,json,pathlib,subprocess,sys
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1]
OUT=BENCH/'results/package-boundary/source';OUT.mkdir(parents=True,exist_ok=True)
TREE=HERE/'target/source-fixtures';TREE.mkdir(parents=True,exist_ok=True)
BINARY=HERE/'target/debug/rnx-package-boundary-probe'
files={
 'app/main.rn':'pub mod atlas; pub mod other; pub fn marker() { 99 } pub fn main() { atlas::value() + other::value() }',
 'deps/one/mod.rn':'pub mod nested; pub mod inline { pub mod leaf; } pub fn marker() { 7 } pub fn value() { self::nested::value() + self::inline::leaf::value() }',
 'deps/one/nested.rn':'pub mod deep; pub fn value() { self::deep::value() + super::marker() }',
 'deps/one/nested/deep.rn':'pub fn value() { 10 }',
 'deps/one/inline/leaf.rn':'pub fn value() { 100 }',
 'deps/two/mod.rn':'pub mod nested; pub fn value() { self::nested::value() }',
 'deps/two/nested.rn':'pub fn value() { 1000 }',
}
for path,text in files.items():
 p=TREE/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
roots={'atlas':str((TREE/'deps/one').resolve()),'other':str((TREE/'deps/two').resolve())}
mapfile=TREE/'roots.json';mapfile.write_text(json.dumps(roots))
entry=(TREE/'app/main.rn').resolve();rows=[]
def run(name,cwd='/tmp'):
 p=subprocess.run([str(BINARY.resolve()),str(entry),str(mapfile.resolve())],cwd=cwd,capture_output=True,text=True,timeout=10)
 assert p.returncode==0,(name,p.stderr)
 j=json.loads(p.stdout);j['case']=name;rows.append(j);return j
j=run('outside-entry-tree');assert j['value']==1117,j
j=run('other-working-directory',str(BENCH));assert j['value']==1117,j
# Alias changes only the consumer declaration and mapping, never package files.
entry.write_text(files['app/main.rn'].replace('atlas','renamed'));roots['renamed']=roots.pop('atlas');mapfile.write_text(json.dumps(roots))
j=run('renamed-dependency');assert j['value']==1117,j
# A file with both candidates retains Rune's mod.rn preference.
p=TREE/'deps/one/nested/deep/mod.rn';p.parent.mkdir(parents=True,exist_ok=True);p.write_text('pub fn value() { 20 }')
j=run('candidate-order');assert j['value']==1127,j;p.unlink()
# A package-level crate reference tests semantic root, not just disk lookup.
p=TREE/'deps/one/mod.rn';p.write_text('pub fn marker() { 7 } pub fn value() { crate::marker() }')
j=run('crate-is-consumer');assert j['value']==1099,j
# Declaring another module in a package does not consult the consumer's sibling map.
p.write_text('pub mod other; pub fn value() { self::other::value() }')
j=run('transitive-name-is-local');assert not j['compile_ok'],j
assert any(e['source'].endswith('deps/one/mod.rn') for e in j['errors']),j
# The physical nested source identity survives runtime faults.
p.write_text(files['deps/one/mod.rn']);q=TREE/'deps/one/nested/deep.rn';q.write_text('pub fn value() {\n    [1][7]\n}')
j=run('runtime-in-dependency');assert j['compile_ok'] and j['origin']['source'].endswith('deps/one/nested/deep.rn') and j['origin']['line']==2,j
q.write_text('pub fn value() {\n    let x = ;\n}')
j=run('compile-in-dependency');assert not j['compile_ok'] and any(e['source'].endswith('deps/one/nested/deep.rn') for e in j['errors']),j
# A use alone never asks the file loader to load a package.
entry.write_text('pub fn main() { renamed::value() }');j=run('no-implicit-discovery');assert not j['compile_ok'] and not j['loads'],j
(OUT/'results.json').write_text(json.dumps({'binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'fixture_sources':files,'rows':rows},indent=2)+'\n')
print('PASS',len(rows),'module-root cases')
