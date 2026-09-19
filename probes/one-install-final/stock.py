from common import *
import random,statistics as st
term=load('term',B/'probes/project-interactive/common.py');cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
bins={'before':T/'baseline','after':T/'stock'};args={'version':['version'],'eval':['--color=never','eval','42'],'json':['--color=never','run',str(B/'scripts/json.rn')],'prompt':['--no-splash','--color=never','repl']}
journal=O/'stock-samples.jsonl';assert not journal.exists();rows=[];expected={}
def quit(t):
 try:
  os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
 finally:t.close()
def sample(mode,kind):
 begin=time.perf_counter_ns()
 if mode=='prompt':
  t=term.Terminal([bins[kind],*args[mode]],T,ENV)
  try:
   out=t.read();ns=time.perf_counter_ns()-begin;assert out=='\r[1] > \r',repr(out)
  finally:quit(t)
 else:
  p=subprocess.run([str(bins[kind]),*args[mode]],cwd=T,env=ENV,capture_output=True,timeout=20);ns=time.perf_counter_ns()-begin
  assert p.returncode==0 and not p.stderr,(mode,kind,p.stdout,p.stderr)
  if mode not in expected:expected[mode]=p.stdout
  assert p.stdout==expected[mode],(mode,kind,p.stdout,expected[mode])
 return ns
def record(x):
 rows.append(x)
 with journal.open('a') as f:f.write(json.dumps(x)+'\n')
for mode in args:
 for kind in bins:
  for _ in range(5):sample(mode,kind)
for repeat in range(2):
 jobs=[(mode,kind,i) for mode in args for kind in bins for i in range(100)];random.Random(675001+repeat).shuffle(jobs)
 for mode,kind,i in jobs:record({'repeat':repeat,'sample':i,'mode':mode,'kind':kind,'ns':sample(mode,kind)})
 ts={k:term.Terminal([p,*args['prompt']],T,ENV) for k,p in bins.items()}
 try:
  for t in ts.values():t.read();assert '] 42\r\n' in t.send('40+2')
  for i in range(200):
   kinds=list(ts);random.Random(675100+repeat*200+i).shuffle(kinds)
   for kind in kinds:
    begin=time.perf_counter_ns();out=ts[kind].send('40+2');ns=time.perf_counter_ns()-begin;assert '] 42\r\n' in out
    record({'repeat':repeat,'sample':i,'mode':'cell','kind':kind,'ns':ns})
 finally:
  for t in ts.values():quit(t)
 print('stock repeat',repeat,'complete',flush=True)
summary=[]
for mode in [*args,'cell']:
 for repeat in range(2):
  d={k:sorted(x['ns']/1e6 for x in rows if x['kind']==k and x['mode']==mode and x['repeat']==repeat) for k in bins}
  med={k:st.median(v) for k,v in d.items()};summary.append({'mode':mode,'repeat':repeat,**med,'delta_ms':med['after']-med['before'],'percent':100*(med['after']/med['before']-1),'p10_p90':{k:[v[len(v)//10],v[len(v)*9//10]] for k,v in d.items()}})
save('stock-summary.json',summary);miss=[m for m in [*args,'cell'] if all(x['percent']>5 for x in summary if x['mode']==m)];save('stock-gate.json',{'passed':not miss,'reproducible_over_five_percent':miss})
save('stock-conditions.json',{'cpu':cpu,'seed':675001,'samples':len(rows),'warmups':5,'binaries':json.loads((O/'binaries.json').read_text()),'commands':args,'outputs':{k:v.decode() for k,v in expected.items()},'clock':'spawn/capture/wait or PTY create-to-prompt; persistent cell send-to-prompt; pinned core, warm, interleaved'})
print(json.dumps(summary,indent=2),flush=True);assert not miss,miss
