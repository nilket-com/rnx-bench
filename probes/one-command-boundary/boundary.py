from common import *
import shutil
s=json.loads((O/'setup.json').read_text());source=Path(s['source'])
consumer=T/'consumer';consumer.mkdir(exist_ok=True);(consumer/'src').mkdir(exist_ok=True)
(consumer/'Cargo.toml').write_text('[package]\nname="runner-only-consumer"\nversion="0.0.0"\nedition="2024"\n[workspace]\n[dependencies]\nrnx={path='+json.dumps(str(source))+',default-features=false,features=["count-allocations"]}\n[profile.release]\nlto="thin"\ncodegen-units=1\nstrip=false\n')
(consumer/'src/main.rs').write_text('fn main()->anyhow::Result<()> {rnx::main_with(rnx::Extensions::none())}\n'.replace('anyhow::Result<()>','Result<(),Box<dyn std::error::Error>>').replace('rnx::main_with(rnx::Extensions::none())','rnx::main_with(rnx::Extensions::none()).map_err(Into::into)'))
run(['cargo','build','--manifest-path',consumer/'Cargo.toml','--release','--offline','--target-dir',T/'build-target'],timeout=1500)
exe=T/'build-target/release/runner-only-consumer';stock=T/'install-git1/bin/rnx'
stock_symbols=run(['nm','-C',stock]).stdout;consumer_symbols=run(['nm','-C',exe]).stdout
assert b'rnx_project::dispatch' in stock_symbols
assert b'rnx_project::' not in consumer_symbols
assert b'RNX_COORD_STATE' not in exe.read_bytes()
meta=json.loads(run(['cargo','metadata','--manifest-path',consumer/'Cargo.toml','--offline','--format-version','1']).stdout)
names={p['name'] for p in meta['packages']}
for absent in ['rnx-project','blake3','toml','sha2']:assert absent not in names,(absent,names)
assert run([exe,'eval','42']).stdout==run([stock,'eval','42']).stdout
result={'consumer_sha256':sha(exe.read_bytes()),'consumer_bytes':exe.stat().st_size,'stock_bytes':stock.stat().st_size,'management_symbol_positive_control':True,'consumer_management_symbols':False,'consumer_packages':sorted(names)}
# Actual graph reachability, not a text search of imports.
meta=json.loads(run(['cargo','metadata','--manifest-path',source/'tools/project/Cargo.toml','--offline','--format-version','1']).stdout)
assert all(p['name']!='rnx' for p in meta['packages']);result['internal_crate_packages']=sorted(p['name'] for p in meta['packages'])
result['audits']={}
for label,path in [('polars','adapters/polars'),('postgres','adapters/postgres'),('server','servers/http-postgres')]:
 meta=json.loads(run(['cargo','metadata','--manifest-path',source/path/'Cargo.toml','--offline','--format-version','1'],timeout=300).stdout)
 ids={p['id']:p['name'] for p in meta['packages']};nodes=meta['resolve']['nodes'];root=[n for n in nodes if ids[n['id']]=='rnx'];assert len(root)==1
 assert 'stock-management' not in root[0]['features'] and 'rnx-project' not in ids.values()
 result['audits'][label]=root[0]['features']
save('boundary.json',result);print('Runner-only symbols, graphs and adapter/server feature audits pass',flush=True)
