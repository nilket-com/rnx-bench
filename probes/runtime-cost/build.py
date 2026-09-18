from pathlib import Path
import os,json,subprocess as sp,time,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/runtime-cost-0064'
state=json.loads((W/'setup.json').read_text());E=state['env'];T=Path(state['tool']);C=Path(state['checkout']);I=Path(state['installed'])
def call(args,timeout=600):
 t=time.perf_counter();p=sp.run(list(map(str,args)),env=E,cwd=W,capture_output=True,text=True,timeout=timeout);elapsed=time.perf_counter()-t;assert p.returncode==0,(args,p.stdout,p.stderr);return p,elapsed
for origin,root in [('checkout',C),('installed',I)]:
 for count,names in [(1,['polars']),(2,['polars','postgres'])]:
  label=f'{origin}-{count}';pdir=W/label;pdir.mkdir(exist_ok=True);m=pdir/'rnx.toml';(pdir/'entry.rn').write_text('pub fn main(_) { polars::lit(1).is_ok() }\n');m.write_text('format=1\n[application]\nentry="entry.rn"\n[runtime]\npath='+json.dumps(str(root))+'\n')
  call([T,'add',*names,'--manifest',m]);_,locktime=call([T,'lock','--offline','--manifest',m]);assert not (pdir/'.rnx/receipt.json').exists()
  lock=json.loads((pdir/'rnx.lock').read_text());key=hashlib.sha256(lock['assembly']['identity'].encode()).hexdigest();assert not (W/'cache/entries'/key/'ready.json').exists()
  result,buildtime=call([T,'build','--offline','--manifest',m]);(O/(label+'-build.log')).write_text(result.stdout+result.stderr)
  receipt=json.loads((pdir/'.rnx/receipt.json').read_text());artifact=next((W/'cache/entries'/key/'artifacts').iterdir());assert artifact.is_file()
  for command in [[T,'run','--manifest',m],[T,'eval','--manifest',m,'--','polars::lit(1).is_ok()']]:assert 'true' in call(command)[0].stdout
  row=dict(label=label,origin=origin,natives=count,manifest=str(m),key=key,artifact=str(artifact),lock_seconds=locktime,cold_build_seconds=buildtime,artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest());state['cells'].append(row);(W/'setup.json').write_text(json.dumps(state,indent=2)+'\n');(O/'setup.json').write_text(json.dumps({k:v for k,v in state.items() if k!='env'},indent=2)+'\n');print('PASS cold assembly',label,buildtime,flush=True)
assert state['cells'][0]['key']!=state['cells'][2]['key'] and state['cells'][1]['key']!=state['cells'][3]['key']
