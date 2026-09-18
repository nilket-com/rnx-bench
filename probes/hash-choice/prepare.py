#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess
BENCH=pathlib.Path(__file__).resolve().parents[2]
HERE=pathlib.Path(__file__).resolve().parent
ROOT=BENCH.parent/'rnx'
RESULT=BENCH/'results/hash-choice-0065'
RESULT.mkdir(exist_ok=True)
def sha(b): return hashlib.sha256(b).hexdigest()
def edit(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)
raw=subprocess.check_output(['git','-C',str(ROOT),'show','7cd3205:tools/project/src/fingerprint.rs']).decode()
# No upstream tests/hooks in this standalone reader experiment. Their omission
# does not remove any ordinary-build production check.
stock=edit(raw,'\n#[cfg(test)]\nmod tests;\n','\n')
stock=edit(stock,'\t#[cfg(test)]\n\ttests::after_open(&path);\n','')
stock=edit(stock,'\t\t#[cfg(feature = "test-support")]\n\t\tcrate::artifact::observed_read(&path, n);\n','')
stock+='''
pub(crate) fn listed(root: &Path, paths: Vec<PathBuf>) -> Result<Tree, String> {
    let mut allowance = Allowance::default();
    for _ in &paths { allowance.entry()?; }
    hash_files(root, paths, &mut allowance)
}
'''
single=edit(stock,'b"rnx-tree-v1\\0"','b"rnx-tree-probe-digests-v2\\0"')
single=edit(single,'\t\tif let Some(tree) = tree.as_mut() {\n\t\t\ttree.update(&buffer[..n]);\n\t\t}\n','')
single=edit(single,'\tOk((\n\t\twire::File {','\tlet digest = content.finalize();\n\tif let Some(tree) = tree.as_mut() { let bytes: &[u8] = digest.as_ref(); tree.update(bytes); }\n\tOk((\n\t\twire::File {')
single=edit(single,'format!("{:x}", content.finalize())','format!("{digest:x}")')
blake=edit(single,'use sha2::{Digest, Sha256};','use crate::BlakeHash as Sha256;')
parallel=edit(blake,'use crate::BlakeHash as Sha256;','use crate::ParallelHash as Sha256;')
sha_large=edit(single,'let mut buffer = [0u8; 16384];','let mut buffer = vec![0u8; 1024 * 1024];')
blake_large=edit(blake,'let mut buffer = [0u8; 16384];','let mut buffer = vec![0u8; 1024 * 1024];')
large=edit(parallel,'let mut buffer = [0u8; 16384];','let mut buffer = vec![0u8; 1024 * 1024];')
archives={}
for name,s in [('stock',stock),('single',single),('blake',blake),('parallel',parallel),('large',large),('sha_large',sha_large),('blake_large',blake_large)]:
    f=HERE/'src'/f'{name}.rs'; f.write_text(s)
subprocess.run(['cargo','fmt','--manifest-path',str(HERE/'Cargo.toml')],check=True)
for name in ['stock','single','blake','parallel','large','sha_large','blake_large']:
    b=(HERE/'src'/f'{name}.rs').read_bytes()
    (RESULT/f'{name}.rs').write_bytes(b); archives[name]=sha(b)
setup=json.loads((BENCH/'results/native-inventory-0065/setup.json').read_text())
c=next(x for x in setup if x['layout']=='shallow' and x['count']==1)
assert sha(pathlib.Path(c['artifact']).read_bytes())==c['artifact_sha256']
inv=json.loads((BENCH/'results/native-inventory-0065/shallow-0-inventory.json').read_text())
# This is the real serialized native inventory from the accepted probe.
print('inventory keys',inv.keys())
trees=inv['inventory']['trees'] if 'inventory' in inv else inv['trees']
tree=trees[0]
config={'root':tree['root'],'paths':[f['path'] for f in tree['files']],'artifact':c['artifact']}
(HERE/'target').mkdir(exist_ok=True)
(HERE/'target/inputs.json').write_text(json.dumps(config,indent=2)+'\n')
(RESULT/'inputs.json').write_text(json.dumps(config,indent=2)+'\n')
(RESULT/'provenance.json').write_text(json.dumps({'root_revision':'7cd3205','input_bench_revision':'c2af5de','original_fingerprint_sha256':sha(raw.encode()),'generated_sources':archives,'runtime_files':len(tree['files']),'runtime_bytes':sum(f['bytes'] for f in tree['files']),'runtime_sha256_v1':tree['sha256'],'artifact_bytes':pathlib.Path(c['artifact']).stat().st_size,'artifact_sha256':sha(pathlib.Path(c['artifact']).read_bytes())},indent=2)+'\n')
