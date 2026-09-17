from common import *
import json,random,statistics,hashlib,tempfile
r=json.loads((P/'.rnx/receipt.json').read_text());A=P/'.rnx/artifacts'/r['executable_sha256'];cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
commands={
 'eval':{'project':[T,'eval','--manifest',P/'rnx.toml','--color=never','--','polars::lit(1).is_ok()'], 'verify':[T,'eval','--manifest',P/'rnx.toml','--verify','--color=never','--','polars::lit(1).is_ok()'], 'direct':[A,'--color=never','eval','polars::lit(1).is_ok()']},
 'session':{'project':[T,'session','--manifest',P/'rnx.toml','--no-splash','--color=never'], 'verify':[T,'session','--manifest',P/'rnx.toml','--verify','--no-splash','--color=never'], 'direct':[A,'--no-splash','--color=never','repl']}}
rows=[];(O/'journal.jsonl').write_text('')
with tempfile.TemporaryDirectory(prefix='rnx-0060-timing-') as tmp:
 cwd=pathlib.Path(tmp);env=dict(ENV,RNX_HISTORY=str(cwd/'history'),RNX_CONFIG=str(cwd/'absent'))
 def sample(mode,kind):
  if mode=='eval':
   start=time.perf_counter_ns();p=call(commands[mode][kind],cwd,env=env);ms=(time.perf_counter_ns()-start)/1e6
   assert p.returncode==0 and p.stdout=='true\n' and not p.stderr,p
  else:
   # Includes PTY allocation/setup and spawn. Ending the session is outside
   # readiness timing but its status is always checked and process reaped.
   start=time.perf_counter_ns();t=Terminal(commands[mode][kind],cwd,env)
   try:
    out=t.read();ms=(time.perf_counter_ns()-start)/1e6;assert out=='\r[1] > \r',repr(out)
    os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
   finally:t.close()
  return ms
 for mode in commands:
  for kind in commands[mode]:sample(mode,kind)
 for repeat in range(2):
  for n in range(20):
   jobs=[(m,k) for m in commands for k in commands[m]];random.Random(60000+repeat*100+n).shuffle(jobs)
   for mode,kind in jobs:
    row={'repeat':repeat,'sample':n,'mode':mode,'kind':kind,'ms':sample(mode,kind)};rows.append(row)
    with (O/'journal.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
  print('repeat',repeat,'complete',flush=True)
summary={m:{k:[statistics.median(x['ms'] for x in rows if x['mode']==m and x['kind']==k and x['repeat']==r) for r in range(2)] for k in commands[m]} for m in commands}
(O/'samples.json').write_text(json.dumps(rows,indent=2)+'\n');(O/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
conditions={'cpu':cpu,'threads':1,'terminal':'xterm-256color','width':120,'height':30,'commands':{m:{k:list(map(str,a)) for k,a in kinds.items()} for m,kinds in commands.items()},'repeats':2,'samples_per_cell':20,'seed':60000,'sample_count':len(rows),'cache':'warm; all samples retained; explicit lock/build and receipt establishment outside timing','eval_clock':'spawn/capture/wait','session_clock':'PTY setup/spawn to full first prompt; :q and reap outside timed interval','binaries':{k:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for k,p in [('tool',T),('artifact',A)]},'rnx_head':subprocess.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip(),'source_patch':'source.patch','rustc':subprocess.check_output(['rustc','-Vv'],text=True)}
(O/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n');print(json.dumps(summary,indent=2))
for mode in summary:
 for repeat in range(2):assert summary[mode]['project'][repeat]-summary[mode]['direct'][repeat]<=25,(mode,'25 ms overhead gate failed')
