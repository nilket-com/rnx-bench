"""Matched ordinary launch and persistent-cell controls; every sample retained."""
from pathlib import Path
import os,sys,json,subprocess,time,random,statistics,hashlib,importlib.util,socket,struct
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/session-final-0063/timing';O.mkdir(parents=True,exist_ok=True)
W=H/'target';D=W/'dogfood';env=json.loads((D/'env.json').read_text());T=D/'bin/rnx-project';P=D/'absolute-project';r=json.loads((P/'.rnx/receipt.json').read_text());A=Path(env['RNX_PROJECT_CACHE'])/'entries'/r['assembly_key']/'artifacts'/r['executable_sha256'];S=D/'bin/rnx';OLD=Path('/tmp/rnx-0063-before/target/release/rnx')
spec=importlib.util.spec_from_file_location('term',B/'probes/project-interactive/common.py');term=importlib.util.module_from_spec(spec);spec.loader.exec_module(term)
cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu});env.update(RNX_HISTORY=str(W/'timing-history'),RNX_CONFIG=str(W/'absent-config'))
commands={'eval':{'project':[T,'eval','--manifest',P/'rnx.toml','--color=never','--','polars::lit(1).is_ok()'],'verify':[T,'eval','--manifest',P/'rnx.toml','--verify','--color=never','--','polars::lit(1).is_ok()'],'direct':[A,'--color=never','eval','polars::lit(1).is_ok()']},'session':{'project':[T,'session','--manifest',P/'rnx.toml','--no-splash','--color=never'],'verify':[T,'session','--manifest',P/'rnx.toml','--verify','--no-splash','--color=never'],'direct':[A,'--no-splash','--color=never','repl']},'version':{k:[p,'version'] for k,p in [('before',OLD),('after',S)]},'stock-eval':{k:[p,'--color=never','eval','42'] for k,p in [('before',OLD),('after',S)]}}
commands['startup-probe']={'direct':[A,'--no-splash','--color=never','repl']}
rows=[];journal=O/'journal.jsonl';journal.write_text('')
def record(row):
 rows.append(row)
 with journal.open('a') as f:f.write(json.dumps(row)+'\n')
def terminal(args):
 t=term.Terminal(args,W,env);t.read();return t
def quit(t):
 os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0;t.close()
def sample(mode,kind):
 start=time.perf_counter_ns()
 if mode=='startup-probe':
  parent,child=socket.socketpair()
  try:
   p=subprocess.Popen(list(map(str,commands[mode][kind])),cwd=W,env=dict(env,RNX_INTERNAL_STARTUP_FD=str(child.fileno())),pass_fds=(child.fileno(),),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   child.close();out,err=p.communicate(timeout=10);parent.settimeout(1);data=b''
   while True:
    b=parent.recv(65536)
    if not b:break
    data+=b
   ms=(time.perf_counter_ns()-start)/1e6
   assert p.returncode==0 and not out and not err and data==struct.pack('!I',9)+bytes([1,6,1])+struct.pack('!I',2)+b'42',(p.returncode,out,err,data)
  finally:
   parent.close();child.close()
   if 'p' in locals() and p.poll() is None:p.kill();p.wait()
 elif mode=='session':
  t=terminal(commands[mode][kind]);ms=(time.perf_counter_ns()-start)/1e6;quit(t)
 else:
  p=subprocess.run(list(map(str,commands[mode][kind])),cwd=W,env=env,capture_output=True,text=True,timeout=20);ms=(time.perf_counter_ns()-start)/1e6
  assert p.returncode==0 and not p.stderr,(mode,kind,p.stdout,p.stderr)
  if mode=='eval':assert p.stdout=='true\n'
  if mode=='stock-eval':assert p.stdout=='42\n'
 return ms
for m,kinds in commands.items():
 for k in kinds:sample(m,k)
for repeat in range(2):
 for n in range(30):
  jobs=[(m,k) for m,kinds in commands.items() for k in kinds];random.Random(630000+repeat*100+n).shuffle(jobs)
  for m,k in jobs:record({'repeat':repeat,'sample':n,'mode':m,'kind':k,'ms':sample(m,k)})
 # Long-lived ordinary cell pairs, no :dep invocation. Startup excluded.
 ts={k:terminal([p,'--no-splash','--color=never','repl']) for k,p in [('before',OLD),('after',S)]}
 try:
  for n in range(100):
   kinds=list(ts);random.Random(631000+repeat*100+n).shuffle(kinds)
   for k in kinds:
    start=time.perf_counter_ns();out=ts[k].send('40 + 2');ms=(time.perf_counter_ns()-start)/1e6;assert '] 42\r\n' in out,out
    record({'repeat':repeat,'sample':n,'mode':'ordinary-cell','kind':k,'ms':ms})
 finally:
  for t in ts.values():quit(t)
 print('repeat',repeat,'complete',flush=True)
summary={m:{k:[statistics.median(x['ms'] for x in rows if x['mode']==m and x['kind']==k and x['repeat']==i) for i in range(2)] for k in sorted({x['kind'] for x in rows if x['mode']==m})} for m in sorted({x['mode'] for x in rows})}
(O/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(O/'conditions.json').write_text(json.dumps({'cpu':cpu,'threads':1,'sample_count':len(rows),'seed':630000,'terminal':'xterm-256color 120x30','cache':'warm; explicit lock/build outside timing','clocks':'spawn/capture/wait, or PTY setup to first prompt; cells send to next prompt','binaries':{k:{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for k,p in [('before',OLD),('after',S),('tool',T),('artifact',A)]},'commands':{m:{k:list(map(str,a)) for k,a in kinds.items()} for m,kinds in commands.items()}},indent=2)+'\n')
print(json.dumps(summary,indent=2))
for m in ['eval','session']:
 for i in range(2):assert summary[m]['project'][i]-summary[m]['direct'][i]<=25,(m,summary[m])
