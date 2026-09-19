from common import *
import random,statistics as st,socket,struct
term=load('measure_term',B/'probes/project-interactive/common.py');env=json.loads((O/'roster-env.json').read_text());rows=json.loads((O/'roster.json').read_text());assert len(rows)==8;cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
cells=[]
for row in rows:
 for mode in ['run','eval','session']:
  for route in ['project','direct']:
   m=Path(row['manifest']);a=row['artifact']
   if route=='project':
    args=[T/'stock','project',mode,'--manifest',m]
    if mode=='eval':args+=['--color=never','--','42']
    if mode=='session':args+=['--no-splash','--color=never']
   else:args=[a,'--no-splash','--color=never']+(['run',m.parent/'entry.rn'] if mode=='run' else ['eval','42'] if mode=='eval' else ['repl'])
   cells.append({'kind':row['kind'],'count':row['count'],'mode':mode,'route':route,'args':list(map(str,args))})
 for mode in ['verify','lock','attach','probe'] if row['count']==1 else []:
  args=[T/'stock','project','eval','--manifest',row['manifest'],'--verify','--','42'] if mode=='verify' else [T/'stock','project','lock' if mode=='lock' else 'build','--offline','--manifest',row['manifest']] if mode!='probe' else [row['artifact'],'--no-splash','--color=never','repl']
  cells.append({'kind':row['kind'],'count':1,'mode':mode,'route':'cost','args':list(map(str,args))})
journal=O/'launch-samples.jsonl';assert not journal.exists();samples=[]
def sample(c):
 begin=time.perf_counter_ns()
 if c['mode']=='session':
  t=term.Terminal(c['args'],T,env)
  try:
   out=t.read();ns=time.perf_counter_ns()-begin;assert out=='\r[1] > \r'
   os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
  finally:t.close()
 elif c['mode']=='probe':
  parent,child=socket.socketpair()
  try:
   p=subprocess.Popen(c['args'],cwd=T,env=env|{'RNX_INTERNAL_STARTUP_FD':str(child.fileno())},pass_fds=(child.fileno(),),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE);child.close();out,err=p.communicate(timeout=10);parent.settimeout(1);data=b''
   while True:
    b=parent.recv(65536)
    if not b:break
    data+=b
   ns=time.perf_counter_ns()-begin;assert p.returncode==0 and not out and not err and data==struct.pack('!I',9)+bytes([1,6,1])+struct.pack('!I',2)+b'42'
  finally:parent.close();child.close()
 else:
  p=subprocess.run(c['args'],cwd=T,env=env,capture_output=True,timeout=30);ns=time.perf_counter_ns()-begin
  assert p.returncode==0,(c,p.stderr)
  if c['mode'] in ['run','eval','verify']:assert p.stdout==b'42\n' and not p.stderr,(c,p.stdout,p.stderr)
  elif c['mode']=='lock':assert b'locked ' in p.stderr
  elif c['mode']=='attach':assert (b'built or attached ' if c['kind']=='git' else b'attached shared assembly ') in p.stderr
 return ns
for c in cells:
 for _ in range(2):sample(c)
with journal.open('w') as f:
 for repeat in range(2):
  jobs=[(c,n) for c in cells for n in range(30)];random.Random(675200+repeat).shuffle(jobs)
  for j,(c,n) in enumerate(jobs):
   row=dict(c,repeat=repeat,sample=n,ns=sample(c));samples.append(row);f.write(json.dumps(row)+'\n');f.flush()
   if j%400==0:print('launch',repeat,j,flush=True)
summary=[]
for repeat in range(2):
 for kind in ['git','path']:
  for mode in ['run','eval','session']:
   prior=None
   for count in range(4):
    values={route:sorted(s['ns']/1e6 for s in samples if s['repeat']==repeat and s['kind']==kind and s['mode']==mode and s['count']==count and s['route']==route) for route in ['project','direct']};med={k:st.median(v) for k,v in values.items()};gap=med['project']-med['direct'];summary.append(dict(repeat=repeat,kind=kind,mode=mode,count=count,**med,over_direct=gap,increment=None if prior is None else gap-prior,p10_p90={k:[v[3],v[27]] for k,v in values.items()}));prior=gap
costs=[dict(kind=k,mode=m,repeat=r,median_ms=st.median(s['ns']/1e6 for s in samples if s['kind']==k and s['mode']==m and s['repeat']==r)) for k in ['git','path'] for m in ['verify','lock','attach','probe'] for r in range(2)]
miss=[]
for g in summary:
 if g['kind']!='git':continue
 p=next(x for x in summary if x['kind']=='path' and all(x[k]==g[k] for k in ['repeat','mode','count']))
 if g['over_direct']>=p['over_direct']:miss.append(g)
save('launch-summary.json',summary);save('cost-summary.json',costs);save('launch-gate.json',{'passed':not miss,'misses':miss,'path_first_adapter_cells':[x for x in summary if x['kind']=='path' and x['count']==1],'path_0065_qualification_unchanged':True});save('launch-conditions.json',{'cpu':cpu,'seed':675200,'warmups':2,'samples':len(samples),'cells':len(cells),'per_cell':30,'repeats':2,'stock_sha256':sha(T/'stock'),'compiled_before_measurement':True,'terminal':'xterm-256color 120x30','clock':'spawn/capture/wait or PTY create-to-prompt; costs are full commands'})
print('launch gate',not miss,flush=True);assert not miss
