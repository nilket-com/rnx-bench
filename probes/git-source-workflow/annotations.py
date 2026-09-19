from common import *
p=T/'tiny-a-clean';lock=json.loads((p/'rnx.lock').read_text());receipt=json.loads((p/'.rnx/receipt.json').read_text());files=[p/'rnx.toml',p/'rnx.lock',p/'rnx.Cargo.lock',p/'.rnx/receipt.json'];before=[(x.read_bytes(),x.stat().st_ino,x.stat().st_mtime_ns) for x in files];rows=[]
for args in [['cache','list'],['cache','remove',receipt['assembly_key'],'--dry-run']]:
 r=run([TOOL,*args,'--manifest',p/'rnx.toml']);doc=json.loads(r.stdout);assert str(p/'rnx.toml') in r.stdout.decode();assert 'indeterminate' not in r.stdout.decode(),doc;rows.append({'args':args,'output':doc})
# No install or selection is needed to identify a Git runtime as Cargo-owned.
root=T/'annotation-runtimes';(root/'entries').mkdir(parents=True,mode=0o700,exist_ok=True);root.chmod(0o700);(root/'install.lock').touch(mode=0o600)
r=run([TOOL,'runtime','list','--root',root,'--manifest',p/'rnx.toml']);doc=json.loads(r.stdout);assert 'Cargo Git runtime' in r.stdout.decode() and 'indeterminate' not in r.stdout.decode();rows.append({'args':['runtime','list'],'output':doc})
assert before==[(x.read_bytes(),x.stat().st_ino,x.stat().st_mtime_ns) for x in files]
save('annotations.json',rows);print('Git project read-only annotations pass',flush=True)
