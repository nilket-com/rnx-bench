"""Uninstrumented three-checkpoint product measurement; preserve every sample."""
from pathlib import Path
import sys,json,os,subprocess as sp,time,random,hashlib,statistics as st,shutil
H=Path('/home/me/work/rnx-bench/probes/nested-position');B=Path('/home/me/work/rnx-bench');R=B.parent/'rnx';W=H/'target';O=B/'results/nested-position-0065';W.mkdir(exist_ok=True);O.mkdir(exist_ok=True)
sys.path.insert(0,str(B/'probes/project-interactive'));from common import Terminal
rows=json.loads((B/'results/inventory-workflow-0065/setup.json').read_text());assert len(rows)==4
E=json.loads((B/'probes/inventory-workflow/target/env.json').read_text());E.update(RNX_HISTORY=str(W/'measurement-history'),RNX_CONFIG=str(W/'absent'),TERM='xterm-256color',POLARS_MAX_THREADS='1')
assert not any(k.startswith('GIT_') for k in E)
prior=B/"probes/nested-inventory/target/recovery/bin ' space/project ' tool"
expected=json.loads((B/'results/nested-inventory-0065/provenance.json').read_text())['binaries'][str(R/'tools/project/target/release/rnx-project')]
assert hashlib.sha256(prior.read_bytes()).hexdigest()==expected
# Freeze the ordinary executables so another feature build cannot replace them.
tools={}
for name,p in {'baseline':B/'probes/native-inventory/target/stock/tools/project/target/release/rnx-project','format':prior,'reuse':R/'tools/project/target/release/rnx-project'}.items():
 q=W/name;assert not q.exists();shutil.copy2(p,q);tools[name]=q
cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu});cells=[]
for row in rows:
 for version in tools:
  fields=row['baseline' if version=='baseline' else 'current'];m=fields['manifest'];a=fields['artifact'];entry=Path(m).parent/'entry.rn'
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
 row=rows[1];fields=row['baseline' if version=='baseline' else 'current'];cells.append(dict(version=version,count=1,mode='eval',route='verify',args=list(map(str,[tools[version],'eval','--manifest',fields['manifest'],'--verify','--','42']))))
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
  for count in range(4):
   b=next(r for r in summary if r['repeat']==repeat and r['mode']==mode and r['version']=='baseline' and r['count']==count)
   c=next(r for r in summary if r['repeat']==repeat and r['mode']==mode and r['version']=='reuse' and r['count']==count)
   if (b['over_direct']-c['over_direct'] < (3 if count==0 else 0)) or (count>0 and c['increment']>=1):failures.append(dict(repeat=repeat,mode=mode,count=count,baseline=b['over_direct'],reuse=c['over_direct'],increment=c['increment']))
(O/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(O/'gate.json').write_text(json.dumps(dict(passed=not failures,failures=failures),indent=2)+'\n')
(O/'measurement.json').write_text(json.dumps(dict(cpu=cpu,threads=1,repeats=2,samples_per_cell=30,cells=len(cells),samples=len(allrows),seed=655001,warmups=2,terminal='xterm-256color',width=120,height=30,scope='matched uninstrumented products, unchanged 443-file runtime and complete copied third adapter; all samples kept',binaries={k:dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for k,p in tools.items()}),indent=2)+'\n')
for mode in ['run','eval','session']:print(mode,{v:[[round(r['over_direct'],3) for r in summary if r['mode']==mode and r['version']==v and r['repeat']==rep] for rep in range(2)] for v in tools},flush=True)
print('gate',not failures,flush=True)
