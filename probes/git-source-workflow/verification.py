from common import *
import shutil,zlib,stat
S=T/'verification';(S/'src').mkdir(parents=True)
(S/'Cargo.toml').write_text('[package]\nname="rnx"\nversion="0.0.0"\n')
(S/'src/lib.rs').write_text('pub const VALUE:u8=1;\n');(S/'.gitignore').write_text('target/\n');(S/'.gitattributes').write_text('src/lib.rs filter=hide\n')
git(S,'init','-q');git(S,'config','filter.hide.clean','sed s/VALUE:u8=2/VALUE:u8=1/g');git(S,'add','.');git(S,'commit','-qm','raw object verifier fixture');rev=git(S,'rev-parse','HEAD').stdout.decode().strip();oid=git(S,'rev-parse','HEAD:src/lib.rs').stdout.decode().strip()
config=T/'verification.json';config.write_text(json.dumps([{'id':'fixture','name':'rnx','url':S.as_uri(),'revision':rev,'checkout':str(S),'manifest':'Cargo.toml'}]))
def verify(ok=True):return run([PROBE,'git-verify',config],ok=ok)
verify();rows=[]
def refuse(name,change,restore):
 change()
 try:
  r=verify(False);assert r.returncode,(name,'accepted');rows.append({'case':name,'stderr':r.stderr.decode()})
 finally:restore()
f=S/'src/lib.rs';original=f.read_bytes()
f.write_bytes(original.replace(b'=1',b'=2'));filtered=git(S,'hash-object','--path=src/lib.rs','src/lib.rs').stdout.decode().strip();assert filtered==oid
r=verify(False);assert r.returncode;rows.append({'case':'hostile-clean-filter-positive-control','filtered_oid_equals_committed':True,'stderr':r.stderr.decode()});f.write_bytes(original)
# Sparse growth is refused before reading half a GiB.
def grow():
 with f.open('r+b') as h:h.truncate(512*1024*1024+1)
refuse('size-allowance-before-content',grow,lambda:f.write_bytes(original))
for name,object_id in [('blob',oid),('commit',rev),('tree',git(S,'rev-parse','HEAD^{tree}').stdout.decode().strip())]:
 path=S/'.git/objects'/object_id[:2]/object_id[2:];saved=path.read_bytes();mode=path.stat().st_mode
 def corrupt():path.chmod(0o600);path.write_bytes(b'not a zlib object')
 refuse('corrupt-'+name,corrupt,lambda:(path.write_bytes(saved),path.chmod(mode)))
 absent=path.with_suffix('.held')
 refuse('missing-'+name,lambda:path.rename(absent),lambda:absent.rename(path))
 # Valid compressed object with its final byte changed under the original OID.
 raw=zlib.decompress(saved);forged=raw[:-1]+bytes([raw[-1]^1])
 def forge():path.chmod(0o600);path.write_bytes(zlib.compress(forged))
 refuse('forged-'+name+'-object-identity',forge,lambda:(path.write_bytes(saved),path.chmod(mode)))
outside=T/'outside-verifier';outside.mkdir();(outside/'lib.rs').write_bytes(original);held=S/'held-src'
refuse('symlink-component',lambda:((S/'src').rename(held),(S/'src').symlink_to(outside,target_is_directory=True)),lambda:((S/'src').unlink(),held.rename(S/'src')))
verify();save('verification.json',rows);print(len(rows),'raw verifier controls pass',flush=True)
