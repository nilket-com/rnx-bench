"""Product launch cost of the reviewed descendant budget and Git fallback."""
from pathlib import Path
import os,json,subprocess as sp,time,random,statistics as st,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/nested-product-0065';T=W/'reuse';rows=json.loads((B/'results/inventory-workflow-0065/setup.json').read_text());row=rows[3];m=Path(row['current']['manifest']);artifact=row['current']['artifact'];root=Path(row['trees'][0]['root']);copy=root/'adapters/pgcopy';target=copy/'target';assert not target.exists()
E=json.loads((B/'probes/inventory-workflow/target/env.json').read_text());assert not any(k.startswith('GIT_') for k in E);E.update(POLARS_MAX_THREADS='1',RNX_CONFIG=str(W/'absent'))
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});journal=O/'fallback-samples.jsonl';assert not journal.exists();allrows=[]
def call(route,e):
 args=[str(T),'eval','--manifest',str(m),'--','42'] if route=='project' else [artifact,'--no-splash','--color=never','eval','42'];start=time.perf_counter_ns();p=sp.run(args,env=e,capture_output=True,text=True,timeout=20);ns=time.perf_counter_ns()-start;assert p.returncode==0 and p.stdout=='42\n' and not p.stderr,(p.stdout,p.stderr);return ns
protected=[m.parent/'rnx.lock',m.parent/'rnx.Cargo.lock',m.parent/'.rnx/receipt.json'];before={str(p):p.read_bytes() for p in protected}
with journal.open('w') as out:
 for shape in ['clean','descendant-budget','git-pager']:
  e=E.copy()
  if shape=='descendant-budget':
   target.mkdir()
   for i in range(4097):(target/str(i)).touch()
   p=sp.run(['git','-C',root,'check-ignore',str(target/'0')],env=e,capture_output=True);assert p.returncode==0
  if shape=='git-pager':e['GIT_PAGER']='cat'
  try:
   for repeat in range(2):
    for route in ['project','direct']:
     for _ in range(2):call(route,e)
    jobs=[(route,i) for route in ['project','direct'] for i in range(30)];random.Random(655500+repeat).shuffle(jobs)
    for route,i in jobs:
     r=dict(shape=shape,repeat=repeat,route=route,sample=i,wall_ns=call(route,e));allrows.append(r);out.write(json.dumps(r)+'\n');out.flush()
   print('PASS measured',shape,flush=True)
  finally:
   if shape=='descendant-budget':shutil.rmtree(target)
assert {str(p):p.read_bytes() for p in protected}==before
summary=[]
for shape in ['clean','descendant-budget','git-pager']:
 for repeat in range(2):
  med={route:st.median(r['wall_ns']/1e6 for r in allrows if r['shape']==shape and r['repeat']==repeat and r['route']==route) for route in ['project','direct']};summary.append(dict(shape=shape,repeat=repeat,**med,over_direct=med['project']-med['direct']))
(O/'fallback.json').write_text(json.dumps(dict(adapters=3,budget=4096,ignored_files=4097,samples=len(allrows),repeats=2,summary=summary,inputs_restored=True,lock_pair_receipt_unchanged=True),indent=2)+'\n')
