from common import *
import copy,shutil
D=json.loads((O/'discovery.json').read_text()); helper=T/'tool/target/release/rnx-project-assembly-probe'
cache=T/'assemblies';cache.mkdir(exist_ok=True)
resolver=T/'discovery'
base=json.loads((O/'metadata.json').read_text())
main=(O/'main.rs').read_text()
roots={'git':Path(D['checkout'])}
path=T/'developer-runtime'
if not path.exists():
 run(['git','clone','--quiet','--no-hardlinks',B.parent/'rnx',path]);git(path,'checkout','--quiet','--detach',REV)
roots['path']=path

def digest(data):
 f=T/'digest-input';f.write_bytes(data);r=T/'digest-output';run([helper,'digest',f,r]);return r.read_text()
def encode(doc):return json.dumps(doc,sort_keys=True,separators=(',',':')).encode()
rows={}
for kind in ['git','path']:
 root=roots[kind]
 if kind=='git':
  meta=base;manifest=(O/'Cargo.toml').read_text()
 else:
  resolver=T/'path-resolver';resolver.mkdir(exist_ok=True);(resolver/'src').mkdir(exist_ok=True)
  manifest='[package]\nname="git-discovery"\nversion="0.0.0"\nedition="2024"\n[workspace]\n[dependencies]\n'+''.join(f'{name}={{path={json.dumps(str(root / suffix))}}}\n' for name,suffix in [('rnx',''),('rnx-polars','adapters/polars'),('rnx-postgres','adapters/postgres')])
  (resolver/'Cargo.toml').write_text(manifest);(resolver/'src/main.rs').write_text(main)
  # Same registry graph seeded from the real Git resolution; Cargo adjusts source IDs.
  (resolver/'Cargo.lock').write_bytes((O/'Cargo.lock').read_bytes())
  p=run(['cargo','metadata','--offline','--format-version=1','--manifest-path',resolver/'Cargo.toml']);meta=json.loads(p.stdout)
  (O/'path-metadata.json').write_bytes(p.stdout)
 audit_meta=copy.deepcopy(meta)
 for pkg in audit_meta['packages']:
  if pkg['name'] in ['rnx','rnx-polars','rnx-postgres']: pkg['source']=None
 m=T/f'{kind}-audit-metadata.json';m.write_text(json.dumps(audit_meta))
 out=T/f'{kind}-inventory.json'
 env=ENV | ({'RNX_PROBE_AUDIT_ONLY':'1'} if kind=='git' else {})
 run([helper,'audit',m,resolver,cache,T/'cargo-home',out],env=env)
 inv=json.loads(out.read_text())
 sources=([{'name':p['name'],'id':p['id'],'source':p['source'],'manifest':p['manifest_path'],'canonical_root':str(Path(p['manifest_path']).parent.resolve())} for p in meta['packages'] if p['name'] in ['rnx','rnx-polars','rnx-postgres']] if kind=='git' else {'packages':inv['packages'],'trees':inv['trees']})
 lock=(resolver/'Cargo.lock').read_bytes()
 context={'cache_root':str(cache.resolve()),'cargo_home':str((T/'cargo-home').resolve()),'rustup_home':str((Path.home()/'.rustup').resolve()),'rustup_toolchain':ENV.get('RUSTUP_TOOLCHAIN'),'rustc':run(['rustc','-Vv']).stdout.decode(),'cargo':run(['cargo','-V']).stdout.decode(),'target':run(['rustc','-Vv']).stdout.decode().split('host: ')[1].splitlines()[0],'profile':'release','features':{'rnx':['default/count-allocations'],'rnx-polars':[],'rnx-postgres':[]},'build_configuration':{'jobs':4,'offline':True,'locked':True,'rustflags':None}}
 identity={'probe_format':1,'generator':'cargo-git-runtime-candidate-v1','context':context,'manifest':manifest,'main':main,'cargo_lock_blake3':digest(lock),'source_kind':kind,'native':sources,'external':inv['external'],'policy':'git coordinates plus retained canonical checkout paths; authentication measured separately, not silently asserted'}
 data=encode(identity);key=digest(data);entry=cache/key
 save(kind+'-identity.json',identity)
 if not entry.exists():
  entry.mkdir();(entry/'src').mkdir();(entry/'Cargo.toml').write_text(manifest);(entry/'src/main.rs').write_text(main);(entry/'Cargo.lock').write_bytes(lock)
  start=time.monotonic();p=run(['cargo','build','--offline','--locked','--release','--manifest-path',entry/'Cargo.toml'],timeout=1200);seconds=time.monotonic()-start
  (O/(kind+'-build.stderr')).write_bytes(p.stderr)
  exe=entry/'target/release/git-discovery';artifact=digest(exe.read_bytes())
  (entry/'ready.json').write_text(json.dumps({'key':key,'artifact_blake3':artifact,'executable':str(exe),'build_seconds':seconds}))
 ready=json.loads((entry/'ready.json').read_text());exe=Path(ready['executable']);assert digest(exe.read_bytes())==ready['artifact_blake3']
 # Actual pipeline through both assembled products; query registration separately requires no DB server.
 output=T/(kind+'-pipeline');output.mkdir(exist_ok=True)
 if not (output/'tiny.parquet').exists():
  p=run([exe,'run',B/'examples/polars/main.rn',output]);(O/(kind+'-pipeline.stdout')).write_bytes(p.stdout)
 p=run([exe,'eval','postgres::query']);assert not p.stderr,p.stderr
 # Two consumers only have application data; each binds the same complete candidate identity.
 for consumer,value in [('a',42),('b',99)]:
  app=T/f'{kind}-consumer-{consumer}';app.mkdir(exist_ok=True);(app/'main.rn').write_text(f'pub fn main(_) {{ println!("{{}}", {value}); }}\n')
  (app/'receipt.json').write_text(json.dumps(ready | {'application':str(app/'main.rn')}))
  request={'entry':str(app/'main.rn'),'manifest':manifest,'main':main,'cargo_lock_blake3':identity['cargo_lock_blake3'],'source_kind':kind}
  (app/'request.json').write_text(json.dumps(request,indent=2));save(kind+'-consumer-'+consumer+'-request.json',request)
  p=run([exe,'run',app/'main.rn']);assert p.stdout.decode().strip()==str(value)
 rows[kind]=ready | {'source_root':str(root),'candidate_identity':kind+'-identity.json'}
 print(kind,'built and both consumers run',ready['build_seconds'],flush=True)
save('assemblies.json',rows)
assert rows['git']['key']!=rows['path']['key']
