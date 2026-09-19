from common import *
s=json.loads((O/'setup.json').read_text());source=Path(s['source']);p=T/'generated-project';p.mkdir(exist_ok=True)
(p/'main.rn').write_text('pub fn main(){42}\n');(p/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath='+json.dumps(str(source))+'\n'+''.join('[native.'+name+']\npath='+json.dumps(str(source/'adapters'/name))+'\npackage="rnx-'+name+'"\nbuilder="build"\nhook="'+('plain' if name=='polars' else 'lifecycle')+'"\n' for name in ['polars','postgres']))
env={k:v for k,v in ENV.items() if k!='CARGO_BUILD_JOBS'}|{'RNX_PROJECT_CACHE':str(T/'generated-cache')}
r=run([T/'install-git1/bin/rnx','project','lock','--manifest',p/'rnx.toml','--offline'],env=env,timeout=300)
lock=json.loads((p/'rnx.lock').read_text());ident=json.loads(lock['assembly']['identity'])
wrapper=T/'generated-graph';wrapper.mkdir(exist_ok=True);(wrapper/'src').mkdir(exist_ok=True);(wrapper/'Cargo.toml').write_text(ident['manifest']);(wrapper/'src/main.rs').write_text(ident['main'])
meta=json.loads(run(['cargo','metadata','--manifest-path',wrapper/'Cargo.toml','--offline','--format-version','1'],env=env,timeout=300).stdout)
ids={p['id']:p['name'] for p in meta['packages']};roots=[n for n in meta['resolve']['nodes'] if ids[n['id']]=='rnx'];assert len(roots)==1
assert 'rnx-project' not in ids.values() and 'stock-management' not in roots[0]['features'] and 'count-allocations' in roots[0]['features'] and 'project-sources' in roots[0]['features']
(O/'generated.Cargo.toml').write_text(ident['manifest']);(O/'generated.main.rs').write_text(ident['main']);save('generated.json',{'rnx_features':roots[0]['features'],'management_in_graph':False,'compiled':False,'note':'actual prototype lock output, Cargo metadata graph with both shipped adapters'})
print('Real generated combined wrapper excludes management and retains allocation accounting',flush=True)
