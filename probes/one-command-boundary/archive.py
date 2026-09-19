from common import *
s=json.loads((O/'setup.json').read_text());src=Path(s['source']);D=T/'schema-tool'
rev=git(src,'rev-parse','HEAD').stdout.decode().strip()
(O/'final-prototype.patch').write_bytes(git(src,'diff',BASE,rev).stdout)
files={}
for root,label in [(src,'integrated'),(D,'schemas')]:
 paths=sorted(p for p in root.rglob('*.rs') if 'target' not in p.relative_to(root).parts and '.git' not in p.relative_to(root).parts)
 files[label]={str(p.relative_to(root)):sha(p.read_bytes()) for p in paths}
# Exact small adapter deltas; new modules are committed as probe source files.
parts=[]
for name in ['assembly_probe.rs','cache_entry.rs']:
 p=run(['git','diff','--no-index','--no-color','--',R/'tools/project/src'/name,D/'src'/name],ok=False);assert p.returncode in [0,1];parts.append(p.stdout)
(O/'schema-adapters.patch').write_bytes(b'\n'.join(parts));save('source-hashes.json',files)
assert git(src,'status','--porcelain').stdout==b''
print('Source bundles, patches and hashes retained',flush=True)
