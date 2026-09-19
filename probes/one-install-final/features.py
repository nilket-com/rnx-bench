from common import *
checks=[]
for name,manifest,flags in [('stock',R/'Cargo.toml',[]),('runner',R/'Cargo.toml',['--no-default-features','--features','count-allocations,project-sources']),('postgres',R/'adapters/postgres/Cargo.toml',[]),('polars',R/'adapters/polars/Cargo.toml',[]),('server',R/'servers/http-postgres/Cargo.toml',[])]:
 p=run(['cargo','tree','--locked','--offline','--manifest-path',manifest,'--prefix','none',*flags]);text=p.stdout.decode();(O/(name+'-tree.txt')).write_text(text);assert ('rnx-project v' in text)==(name=='stock')
 if name in ['stock','runner']:assert 'polars v' not in text and 'tokio-postgres v' not in text
 checks.append({'name':name,'management':name=='stock'})
for row in json.loads((O/'roster.json').read_text()):
 if row['count']!=2:continue
 text=run(['nm','-C',row['artifact']]).stdout;assert b'rnx_project::' not in text;checks.append({'generated':row['kind'],'management_symbols':False,'artifact_sha256':sha(row['artifact'])})
p=run(['cargo','test','--locked','--offline','--test','release_metadata','--','--test-threads=1']);(O/'final-packaged-manifest.log').write_bytes(p.stdout+p.stderr)
save('feature-checks.json',checks);print('feature and final packaged-manifest checks passed',flush=True)
