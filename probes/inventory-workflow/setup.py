"""Format-only controls reuse the accepted, unchanged 443-file native roster."""
from pathlib import Path
import json,os,subprocess as sp,time,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/inventory-workflow-0065';W.mkdir(exist_ok=True);O.mkdir(exist_ok=True)
I=B/'probes/native-inventory/target';T=R/'tools/project/target/release/rnx-project';OLD=I/'stock/tools/project/target/release/rnx-project'
E=json.loads((I/'env.json').read_text());E['PYTHONDONTWRITEBYTECODE']='1'
rows=json.loads((B/'results/native-inventory-0065/setup.json').read_text());out=[]
def call(args):
 p=sp.run(list(map(str,args)),env=E,cwd=W,capture_output=True,text=True,timeout=1200)
 assert p.returncode==0,(args,p.stdout,p.stderr)
 return p
for old in rows:
 if old['layout']!='shallow':continue
 count=old['count'];a=W/f'current-{count}';a.mkdir();m=a/'rnx.toml';m.write_bytes(Path(old['manifest']).read_bytes());(a/'entry.rn').write_bytes((Path(old['manifest']).parent/'entry.rn').read_bytes())
 (a/'rnx.Cargo.lock').write_bytes((Path(old['manifest']).parent/'rnx.Cargo.lock').read_bytes())
 p=call([T,'lock','--offline','--manifest',m]);assert (a/'rnx.Cargo.lock').read_bytes()==(Path(old['manifest']).parent/'rnx.Cargo.lock').read_bytes();(O/f'lock-{count}.log').write_text(p.stdout+p.stderr)
 t=time.monotonic();p=call([T,'build','--offline','--manifest',m]);sec=time.monotonic()-t;(O/f'build-{count}.log').write_text(p.stdout+p.stderr)
 lock=json.loads((a/'rnx.lock').read_text());r=json.loads((a/'.rnx/receipt.json').read_text());assert lock['format']==3 and r['format']==4
 artifact=Path(E['RNX_PROJECT_CACHE'])/'entries'/r['assembly_key']/'artifacts'/r['executable_blake3'];assert r['assembly_key']!=old['key']
 assert call([T,'eval','--manifest',m,'--','42']).stdout=='42\n'
 assert call([OLD,'eval','--manifest',old['manifest'],'--','42']).stdout=='42\n'
 native=lock['inputs']['native'];trees=[dict(root=t['root'],files=len(t['files']),bytes=sum(f['bytes'] for f in t['files']),blake3=t['blake3']) for t in native['trees']]
 assert sorted((t['root'],t['files'],t['bytes']) for t in trees)==sorted((t['root'],t['files'],t['bytes']) for t in old['trees'])
 out.append(dict(count=count,baseline=dict(manifest=old['manifest'],artifact=old['artifact']),current=dict(manifest=str(m),artifact=str(artifact)),trees=trees,build_seconds=sec,artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest()))
 (O/'setup.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS current build',count,round(sec,2),flush=True)
(W/'env.json').write_text(json.dumps(E))
(O/'tools.json').write_text(json.dumps({k:dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for k,p in [('baseline',OLD),('current',T)]},indent=2)+'\n')
