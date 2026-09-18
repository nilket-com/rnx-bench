"""Full product topology slopes and path controls, ordinary final executable."""
from pathlib import Path
import json,os,subprocess as sp,time,random,statistics as st,sys,shutil,collections
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/inventory-final-0065';T=W/'tool';E=json.loads((W/'env.json').read_text());E.update(RNX_HISTORY=str(W/'topology-history'),RNX_CONFIG=str(W/'absent'));assert not any(k.startswith('GIT_') for k in E)
sys.path.insert(0,str(B/'probes/project-interactive'));from common import Terminal
rows=json.loads((O/'topology-setup.json').read_text());eligible=[r for r in rows if r['shape']=='eligible'];root=Path(eligible[0]['trees'][0]['root']);adapters=[root/'adapters'/x for x in ['polars','postgres','pgcopy']]
rows += [dict(r,shape='git-editor') for r in eligible]+[dict(r,shape='nested-repository') for r in eligible]
cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu});cells=[]
for r in rows:
 for mode in ['run','eval','session']:
  for route in ['project','direct']:
   if route=='project':
    args=[str(T),mode,'--manifest',r['manifest']]
    if mode=='eval':args+=['--color=never','--','42']
    if mode=='session':args+=['--no-splash','--color=never']
   else:args=[r['artifact'],'--no-splash','--color=never']+(['run',str(Path(r['manifest']).parent/'entry.rn')] if mode=='run' else ['eval','42'] if mode=='eval' else ['repl'])
   cells.append(dict(shape=r['shape'],count=r['count'],mode=mode,route=route,args=args))
protected={p:p.read_bytes() for r in rows for p in [Path(r['manifest']).parent/'rnx.lock',Path(r['manifest']).parent/'rnx.Cargo.lock',Path(r['manifest']).parent/'.rnx/receipt.json']}
def sample(c):
 env=E|({'GIT_EDITOR':'true'} if c['shape']=='git-editor' else {});start=time.perf_counter_ns()
 if c['mode']=='session':
  t=Terminal(c['args'],W,env)
  try:
   out=t.read();ns=time.perf_counter_ns()-start;assert out=='\r[1] > \r',repr(out);os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
  finally:t.close()
 else:
  p=sp.run(c['args'],cwd=W,env=env,capture_output=True,text=True,timeout=20);ns=time.perf_counter_ns()-start;assert p.returncode==0 and p.stdout=='42\n' and not p.stderr,(c,p.stdout,p.stderr)
 return ns
probe=B.parent/'rnx/tools/project/target/debug/rnx-project-assembly-probe';counters=[]
def inspect(shape,n):
 rs=[root]+adapters[:n] if shape in ['eligible','nested-repository','git-editor'] else [Path(t['root']) for t in next(r for r in rows if r['shape']==shape and r['count']==n)['trees']]
 q=W/'topology-probe.json';q.write_text(json.dumps(dict(roots=list(map(str,rs)),candidate=True,entries=100000,bytes=512*1024*1024)));env=E|({'GIT_EDITOR':'true'} if shape=='git-editor' else {});p=sp.run([probe,'nested-inventory',q],env=env,capture_output=True,text=True,timeout=30);assert p.returncode==0,p.stderr;ans=json.loads(p.stdout);assert 'Ok' in ans['answer'];events=ans['events'];calls=sum('git' in v for v in events);reuse=sum('reuse' in v for v in events);expected=3 if shape in ['eligible','deep','long'] else 3*(n+1);assert calls==expected,(shape,n,calls);counters.append(dict(shape=shape,count=n,git=calls,reuses=reuse,reads=sum('read' in v for v in events)))
journal=O/'topology-samples.jsonl';assert not journal.exists();samples=[]
with journal.open('w') as f:
 for nested in [False,True]:
  selected=[c for c in cells if (c['shape']=='nested-repository')==nested]
  created=[]
  try:
   if nested:
    for a in adapters:
     assert not (a/'.git').exists();sp.run(['git','init','-q',a],env=E,check=True);created.append(a/'.git');sp.run(['git','-C',a,'add','.'],env=E,check=True)
   for shape,n in sorted(set((c['shape'],c['count']) for c in selected)):inspect(shape,n)
   for c in selected:
    for _ in range(2):sample(c)
   for repeat in range(2):
    jobs=[(c,i) for c in selected for i in range(30)];random.Random(656100+repeat+int(nested)*10).shuffle(jobs)
    for j,(c,i) in enumerate(jobs):
     r=dict(c,repeat=repeat,sample=i,wall_ns=sample(c));samples.append(r);f.write(json.dumps(r)+'\n');f.flush()
     if j%750==0:print('topology',nested,repeat,j,flush=True)
  finally:
   for p in created:shutil.rmtree(p)
assert all(p.read_bytes()==raw for p,raw in protected.items());assert all(not (a/'.git').exists() for a in adapters)
summary=[]
for shape in sorted(set(c['shape'] for c in cells)):
 for repeat in range(2):
  for mode in ['run','eval','session']:
   gaps=[]
   for n in sorted(set(c['count'] for c in cells if c['shape']==shape)):
    med={route:st.median(r['wall_ns']/1e6 for r in samples if r['shape']==shape and r['repeat']==repeat and r['mode']==mode and r['count']==n and r['route']==route) for route in ['project','direct']};gap=med['project']-med['direct'];summary.append(dict(shape=shape,repeat=repeat,mode=mode,count=n,**med,over_direct=gap,increment=gap-gaps[-1] if gaps else None));gaps.append(gap)
   if len(gaps)==4:
    slope=sum((i-1.5)*g for i,g in enumerate(gaps))/5
    for r in summary[-4:]:r['slope']=slope
(O/'topology-summary.json').write_text(json.dumps(summary,indent=2)+'\n');(O/'topology-counters.json').write_text(json.dumps(counters,indent=2)+'\n');(O/'topology-measurement.json').write_text(json.dumps(dict(cpu=cpu,samples=len(samples),cells=len(cells),repeats=2,samples_per_cell=30,warmups=2,seed=656100,blocks='non-nested shapes interleaved together; temporary nested Git administration in a separate block',inputs_restored=True,terminal='xterm-256color 120x30',runtime_constant='443 files including all three adapter contents at every roster count',external_difference='adapter Cargo.toml runtime path rewritten to fixed canonical runtime; no other adapter source change; ordinary root tree is unchanged'),indent=2)+'\n');print('PASS topology measurements',len(samples),flush=True)
