"""Real external adapter builds and equal-byte path controls; retain all entries."""
from pathlib import Path
import subprocess as sp,json,os,shutil,time,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/inventory-final-0065';T=W/'tool'
deps=R/'tools/project/target/release/deps';lib=max(deps.glob('libblake3-*.rlib'),key=lambda p:p.stat().st_mtime_ns)
sp.run(['rustc','--edition=2024',H/'b3.rs','-L','dependency='+str(deps),'--extern','blake3='+str(lib),'-o',W/'b3'],check=True)
assert not T.exists();shutil.copy2(R/'tools/project/target/release/rnx-project',T)
expected=json.loads((B/'results/nested-position-0065/measurement.json').read_text())['binaries']['reuse']['sha256'];assert hashlib.sha256(T.read_bytes()).hexdigest()==expected
E=json.loads((B/'probes/inventory-workflow/target/env.json').read_text());assert not any(k.startswith('GIT_') for k in E);E.update(RNX_CONFIG=str(W/'absent'),POLARS_MAX_THREADS='1',TERM='xterm-256color',PYTHONDONTWRITEBYTECODE='1');(W/'env.json').write_text(json.dumps(E))
base=json.loads((B/'results/inventory-workflow-0065/setup.json').read_text());runtime=Path(base[0]['trees'][0]['root']);aliases=['polars','postgres','pgcopy'];out=[]
def call(args,label):
 start=time.monotonic();p=sp.run(list(map(str,args)),env=E,cwd=W,capture_output=True,text=True,timeout=1200);(O/(label+'.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,(label,p.stderr);return p,time.monotonic()-start
for row in base:out.append(dict(shape='eligible',count=row['count'],**row['current'],trees=row['trees']))
external=W/'external';external.mkdir()
for name in aliases:
 src=runtime/'adapters'/name;dst=external/name;dst.mkdir()
 names=sp.check_output(['git','-C',src,'ls-files','-z','--','.'],env=E).decode().split('\0')
 for rel in filter(None,names):
  p=dst/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src/rel,p)
 p=dst/'Cargo.toml';s=p.read_text();assert 'path = "../.."' in s;s=s.replace('path = "../.."','path = '+json.dumps(str(runtime)));p.write_text(s)
 sp.run(['git','init','-q',dst],env=E,check=True);sp.run(['git','-C',dst,'add','.'],env=E,check=True)
layouts=json.loads((B/'results/native-inventory-0065/provenance.json').read_text())['layouts']
requests=[('external',n,runtime,[external/a for a in aliases[:n]]) for n in [1,2,3]]+[(shape,2,Path(layouts[shape]),[Path(layouts[shape])/'adapters'/a for a in aliases[:2]]) for shape in ['deep','long']]
out.append(dict(out[0],shape='external'))
for shape,n,rt,adapters in requests:
 name=f'{shape}-{n}';d=W/name;d.mkdir();m=d/'rnx.toml';(d/'entry.rn').write_text('pub fn main(_) { 42 }\n');text='format=1\n[application]\nentry="entry.rn"\n[runtime]\npath='+json.dumps(str(rt))+'\n'
 for alias,path in zip(aliases,adapters):text+='[native.'+alias+']\npath='+json.dumps(str(path))+'\npackage="rnx-'+alias+'"\nbuilder="build"\nhook="'+('plain' if alias=='polars' else 'lifecycle')+'"\n'
 m.write_text(text);seed=Path(base[n]['current']['manifest']).parent/'rnx.Cargo.lock';(d/'rnx.Cargo.lock').write_bytes(seed.read_bytes());call([T,'lock','--offline','--manifest',m],name+'-lock');assert (d/'rnx.Cargo.lock').read_bytes()==seed.read_bytes()
 _,sec=call([T,'build','--offline','--manifest',m],name+'-build');r=json.loads((d/'.rnx/receipt.json').read_text());a=Path(E['RNX_PROJECT_CACHE'])/'entries'/r['assembly_key']/'artifacts'/r['executable_blake3'];p,_=call([T,'eval','--manifest',m,'--','42'],name+'-eval');assert p.stdout=='42\n'
 lock=json.loads((d/'rnx.lock').read_text());trees=[dict(root=t['root'],files=len(t['files']),bytes=sum(f['bytes'] for f in t['files']),blake3=t['blake3']) for t in lock['inputs']['native']['trees']]
 out.append(dict(shape=shape,count=n,manifest=str(m),artifact=str(a),trees=trees,build_seconds=sec,external_candidates=len(lock['inputs']['native']['external']),artifact_sha256=hashlib.sha256(a.read_bytes()).hexdigest()));(O/'topology-setup.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS topology build',name,round(sec,2),flush=True)
for shape in ['deep','long']:
 row=next(r for r in out if r['shape']==shape);canon=lambda x:sorted((t['files'],t['bytes'],t['blake3']) for t in x['trees']);assert canon(row)==canon(out[2])
print('PASS topology setup; path-control tracked bytes equal; external Cargo runtime path intentionally differs')
