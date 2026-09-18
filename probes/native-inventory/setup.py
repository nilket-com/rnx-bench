"""Actual lock graphs, fixed-target inventory inputs and real launch controls."""
from pathlib import Path
import os,subprocess as sp,json,hashlib,time
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/native-inventory-0065';prov=json.loads((O/'provenance.json').read_text())
T=W/'stock/tools/project/target/release/rnx-project';P=W/'stock/tools/project/target/release/inventory-probe'
E={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','GIT_','CARGO_','RUST'))};E.update(RNX_PROJECT_CACHE=str(W/'cache'),POLARS_MAX_THREADS='1',RNX_CONFIG=str(W/'absent-settings'),TERM='xterm-256color')
rows=[]
def call(a,timeout=600):
 p=sp.run(list(map(str,a)),env=E,cwd=W,capture_output=True,text=True,timeout=timeout);assert p.returncode==0,(a,p.stdout,p.stderr);return p
for layout,root in prov['layouts'].items():
 root=Path(root)
 for count in range(4):
  name=f'{layout}-{count}';d=W/name;d.mkdir();m=d/'rnx.toml';(d/'entry.rn').write_text('pub fn main(_) { 42 }\n')
  text='format=1\n[application]\nentry="entry.rn"\n[runtime]\npath='+json.dumps(str(root))+'\n'
  for alias in ['polars','postgres','pgcopy'][:count]:
   text+='[native.'+alias+']\npath='+json.dumps(str(root/'adapters'/alias))+'\npackage="rnx-'+alias+'"\nbuilder="build"\nhook="'+('plain' if alias=='polars' else 'lifecycle')+'"\n'
  m.write_text(text);r=call([T,'lock','--offline','--manifest',m]);(O/(name+'-lock.log')).write_text(r.stdout+r.stderr)
  lock=json.loads((d/'rnx.lock').read_text());identity=json.loads(lock['assembly']['identity']);key=hashlib.sha256(lock['assembly']['identity'].encode()).hexdigest();native=lock['inputs']['native']
  stage=W/'cache/entries'/key/'assembly'
  config=dict(metadata=dict(workspace_root=str(stage),packages=[dict(id=p['id'],name=p['name'],source=None,manifest_path=p['manifest']) for p in native['packages']]),stage=str(stage),invocation=str(W/'cache'),home=str(Path.home()/'.cargo'),expected=None,executable=str(W/'fixed-rnx'))
  cfg=W/(name+'.json');cfg.write_text(json.dumps(config))
  answer=json.loads(call([P,cfg]).stdout);assert answer['inventory']==native
  config['expected']=answer['digest'];cfg.write_text(json.dumps(config));(O/(name+'-inventory.json')).write_text(json.dumps(answer,indent=2)+'\n')
  assert call([P,cfg]).stdout=='42\n'
  trees=[dict(root=t['root'],files=len(t['files']),bytes=sum(f['bytes'] for f in t['files']),sha256=t['sha256']) for t in native['trees']]
  row=dict(layout=layout,count=count,manifest=str(m),config=str(cfg),trees=trees,key=key,external_candidates=len(native['external']),external_present=sum(x['file'] is not None for x in native['external']))
  rows.append(row);print('PASS inventory',name,[(t['files'],t['bytes']) for t in trees],flush=True)
# Exactly equal tracked working bytes across path controls, including the renamed copy.
for count in range(4):
 a=[r for r in rows if r['count']==count]
 canon=lambda r:sorted((t['files'],t['bytes'],t['sha256']) for t in r['trees'])
 assert all(canon(r)==canon(a[0]) for r in a)
(W/'env.json').write_text(json.dumps(E,indent=2)+'\n')
(O/'setup.json').write_text(json.dumps(rows,indent=2)+'\n')
# Actual product controls at one layout. Setup time is separate, no cold-build claim.
for row in rows:
 if row['layout']!='shallow':continue
 t=time.monotonic();r=call([T,'build','--offline','--manifest',row['manifest']],timeout=1200)
 (O/(f"product-{row['count']}-build.log")).write_text(r.stdout+r.stderr)
 receipt=json.loads((Path(row['manifest']).parent/'.rnx/receipt.json').read_text());artifact=W/'cache/entries'/receipt['assembly_key']/'artifacts'/receipt['executable_sha256'];row.update(artifact=str(artifact),build_seconds=time.monotonic()-t,artifact_sha256=receipt['executable_sha256'])
 assert call([T,'eval','--manifest',row['manifest'],'--','42']).stdout=='42\n'
 assert call([artifact,'--no-splash','--color=never','eval','42']).stdout=='42\n'
 (O/'setup.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS product control',row['count'],row['build_seconds'],flush=True)
