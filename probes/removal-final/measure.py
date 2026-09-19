"""Uninstrumented pre-removal versus final product measurement; preserve every sample."""
from pathlib import Path
import sys,json,os,subprocess as sp,time,random,hashlib,statistics as st,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/removal-final-0066/launch';W.mkdir(exist_ok=True);O.mkdir(exist_ok=True)
sys.path.insert(0,str(B/'probes/project-interactive'));from common import Terminal
rows=json.loads((B/'results/inventory-workflow-0065/setup.json').read_text());assert len(rows)==4
E=json.loads((B/'probes/inventory-workflow/target/env.json').read_text());E.update(RNX_HISTORY=str(W/'measurement-history'),RNX_CONFIG=str(W/'absent'),TERM='xterm-256color',POLARS_MAX_THREADS='1')
assert not any(k.startswith('GIT_') for k in E)
prior=B/'probes/inventory-final/target/reuse'
expected=json.loads((B/'results/inventory-final-0065/headline/measurement.json').read_text())['binaries']['reuse']['sha256']
assert hashlib.sha256(prior.read_bytes()).hexdigest()==expected
assert not sp.check_output(['git','-C',R,'diff','4855dbd','d7d8b0d','--','tools/project/src'])
tools={}
for name,p in {'before':prior,'after':W/'tool-ordinary'}.items():
 q=W/('launch-'+name);assert not q.exists();shutil.copy2(p,q);tools[name]=q
cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu});cells=[]
for row in rows:
 for version in tools:
  fields=row['current'];m=fields['manifest'];a=fields['artifact'];entry=Path(m).parent/'entry.rn'
  for mode in ['run','eval','session']:
   for route in ['project','direct']:
    if route=='project':
     args=[tools[version],mode,'--manifest',m]
     if mode=='eval':args+=['--color=never','--','42']
     if mode=='session':args+=['--no-splash','--color=never']
    else:
     args=[a,'--no-splash','--color=never'];args+=['run',entry] if mode=='run' else ['eval','42'] if mode=='eval' else ['repl']
    cells.append(dict(version=version,count=row['count'],mode=mode,route=route,args=list(map(str,args))))
for version in tools:
 row=rows[1];fields=row['current'];cells.append(dict(version=version,count=1,mode='eval',route='verify',args=list(map(str,[tools[version],'eval','--manifest',fields['manifest'],'--verify','--','42']))))
def sample(c):
 start=time.perf_counter_ns()
 if c['mode']=='session':
  t=Terminal(c['args'],W,E)
  try:
   out=t.read();ns=time.perf_counter_ns()-start;assert out=='\r[1] > \r',repr(out)
   os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
  finally:t.close()
 else:
  p=sp.run(c['args'],cwd=W,env=E,capture_output=True,text=True,timeout=15);ns=time.perf_counter_ns()-start
  assert p.returncode==0 and p.stdout=='42\n' and not p.stderr,(c,p.returncode,p.stdout,p.stderr)
 return ns
protected={p:p.read_bytes() for r in rows for p in [Path(r['current']['manifest']).parent/'rnx.lock',Path(r['current']['manifest']).parent/'rnx.Cargo.lock',Path(r['current']['manifest']).parent/'.rnx/receipt.json']}
journal=O/'samples.jsonl';assert not journal.exists(),'retain previous journal'
for c in cells:
 for _ in range(2):sample(c)
allrows=[]
with journal.open('w') as f:
 for repeat in range(2):
  jobs=[(c,i) for c in cells for i in range(30)];random.Random(655001+repeat).shuffle(jobs)
  for j,(c,i) in enumerate(jobs):
   r=dict(c,repeat=repeat,sample=i,wall_ns=sample(c));f.write(json.dumps(r,separators=(',',':'))+'\n');f.flush();allrows.append(r)
   if j%500==0:print('progress',repeat,j,flush=True)
  print('PASS repeat',repeat,len(jobs),'samples',flush=True)
summary=[];failures=[]
for repeat in range(2):
 for mode in ['run','eval','session']:
  for version in tools:
   gaps=[]
   for count in range(4):
    med={route:st.median(r['wall_ns']/1e6 for r in allrows if r['repeat']==repeat and r['mode']==mode and r['version']==version and r['count']==count and r['route']==route) for route in ['project','direct']}
    gap=med['project']-med['direct'];summary.append(dict(repeat=repeat,mode=mode,version=version,count=count,**med,over_direct=gap,increment=None if not gaps else gap-gaps[-1]));gaps.append(gap)
   slope=sum((i-1.5)*v for i,v in enumerate(gaps))/5
   for r in summary[-4:]:r['slope']=slope
(O/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(O/'first-adapter.json').write_text(json.dumps([r for r in summary if r['count']==1],indent=2)+'\n')
(O/'measurement.json').write_text(json.dumps(dict(cpu=cpu,threads=1,repeats=2,samples_per_cell=30,cells=len(cells),samples=len(allrows),seed=655001,warmups=2,terminal='xterm-256color',width=120,height=30,scope='matched uninstrumented products, unchanged 443-file runtime and complete copied third adapter; all samples kept',binaries={k:dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for k,p in tools.items()}),indent=2)+'\n')
for mode in ['run','eval','session']:print(mode,{v:[[round(r['over_direct'],3) for r in summary if r['mode']==mode and r['version']==v and r['repeat']==rep] for rep in range(2)] for v in tools},flush=True)
print('PASS matched removal launch measurement; prior qualification unchanged',flush=True)

assert all(p.read_bytes()==v for p,v in protected.items())
