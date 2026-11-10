"""Matched format-only product timings; no nested inventory reuse or clocks."""
from pathlib import Path
import sys,json,os,subprocess as sp,time,random,hashlib,statistics as st
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/inventory-workflow-0065'
sys.path.insert(0,str(B/'probes/project-interactive'));from common import Terminal
rows=json.loads((O/'setup.json').read_text());assert len(rows)==4
E=json.loads((W/'env.json').read_text());E.update(RNX_HISTORY=str(W/'measurement-history'),RNX_CONFIG=str(W/'absent'),TERM='xterm-256color',POLARS_MAX_THREADS='1')
tools={'baseline':B/'probes/native-inventory/target/stock/tools/project/target/release/rnx-project','current':B.parent/'rnx/tools/project/target/release/rnx-project'}
cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu});cells=[]
for row in rows:
 for version in tools:
  m=row[version]['manifest'];a=row[version]['artifact'];entry=Path(m).parent/'entry.rn'
  for mode in ['run','eval','session']:
   for route in ['project','direct']:
    if route=='project':
     args=[tools[version],mode,'--manifest',m]
     if mode=='eval':args+=['--color=never','--','42']
     if mode=='session':args+=['--no-splash','--color=never']
    else:
     args=[a,'--no-splash','--color=never']
     args+=['run',entry] if mode=='run' else ['eval','42'] if mode=='eval' else ['repl']
    cells.append(dict(version=version,count=row['count'],mode=mode,route=route,args=list(map(str,args))))
# Full verify has its own row; never averaged into everyday launch.
for version in tools:
 row=rows[1];cells.append(dict(version=version,count=1,mode='eval',route='verify',args=list(map(str,[tools[version],'eval','--manifest',row[version]['manifest'],'--verify','--','42']))))
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
journal=O/'samples.jsonl';assert not journal.exists(),'retain or move existing journal before rerunning'
for c in cells:
 for _ in range(2):sample(c)
allrows=[]
with journal.open('w') as f:
 for repeat in range(2):
  jobs=[(c,i) for c in cells for i in range(30)];random.Random(652001+repeat).shuffle(jobs)
  for c,i in jobs:
   r=dict(c,repeat=repeat,sample=i,wall_ns=sample(c));f.write(json.dumps(r,separators=(',',':'))+'\n');f.flush();allrows.append(r)
  print('PASS repeat',repeat,len(jobs),'samples',flush=True)
summary=[]
for repeat in range(2):
 for mode in ['run','eval','session']:
  for version in tools:
   gaps=[]
   for count in range(4):
    med={route:st.median(r['wall_ns']/1e6 for r in allrows if r['repeat']==repeat and r['mode']==mode and r['version']==version and r['count']==count and r['route']==route) for route in ['project','direct']}
    gap=med['project']-med['direct'];summary.append(dict(repeat=repeat,mode=mode,version=version,count=count,**med,over_direct=gap,increment=None if not gaps else gap-gaps[-1]));gaps.append(gap)
   slope=sum((i-1.5)*v for i,v in enumerate(gaps))/5
   for r in summary[-4:]:r['slope']=slope
(O/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(O/'measurement.json').write_text(json.dumps(dict(cpu=cpu,threads=1,terminal='xterm-256color',width=120,height=30,repeats=2,samples_per_cell=30,cells=len(cells),samples=len(allrows),seed=652001,warmups=2,scope='matched uninstrumented products, unchanged accepted 443-file runtime plus complete renamed adapter; warm single-host Linux; each product has its own direct artifact; no samples discarded',session_clock='PTY allocation/spawn to full first prompt, quit/reap outside timing',other_clock='spawn/capture/wait',binaries={k:dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for k,p in tools.items()}),indent=2)+'\n')
for mode in ['run','eval','session']:
 print(mode,{v:[[round(r['over_direct'],3) for r in summary if r['mode']==mode and r['version']==v and r['repeat']==rep] for rep in range(2)] for v in tools})
