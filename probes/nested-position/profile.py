"""Exclusive test-support phases, separately interleaved with ordinary launch."""
from pathlib import Path
import json,os,subprocess as sp,time,random,statistics as st,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/nested-position-0065';rows=json.loads((B/'results/inventory-workflow-0065/setup.json').read_text());E=json.loads((B/'probes/inventory-workflow/target/env.json').read_text());E.update(POLARS_MAX_THREADS='1',RNX_CONFIG=str(W/'absent'))
assert not any(k.startswith('GIT_') for k in E);cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
journal=O/'profile-samples.jsonl';assert not journal.exists();phases=O/'phases.jsonl';assert not phases.exists();cells=[(n,mode) for n in range(4) for mode in ['ordinary','profiled']];samples=[]
def call(n,mode):
 row=rows[n];tool=W/('reuse' if mode=='ordinary' else 'profiled');env=E|({'RNX_INVENTORY_PROFILE':str(phases)} if mode=='profiled' else {})
 start=time.perf_counter_ns();p=sp.run([tool,'eval','--manifest',row['current']['manifest'],'--','42'],env=env,capture_output=True,text=True,timeout=15);ns=time.perf_counter_ns()-start;assert p.returncode==0 and p.stdout=='42\n' and not p.stderr,(p.stdout,p.stderr)
 entries=[]
 if mode=='profiled':
  entries=[json.loads(line) for line in phases.read_text().splitlines()];phases.unlink()
  assert len(entries)==1,entries
  for e in entries:assert sum(e['phase_ns'].values())==e['wall_ns']
 return dict(count=n,mode=mode,wall_ns=ns,inventory=entries)
for n,mode in cells:
 for _ in range(2):call(n,mode)
with journal.open('w') as f:
 for repeat in range(2):
  jobs=[(n,mode,i) for n,mode in cells for i in range(30)];random.Random(655800+repeat).shuffle(jobs)
  for n,mode,i in jobs:
   r=call(n,mode)|dict(repeat=repeat,sample=i);samples.append(r);f.write(json.dumps(r)+'\n');f.flush()
  print('PASS profile repeat',repeat,flush=True)
summary=[]
for repeat in range(2):
 for n in range(4):
  a=[r for r in samples if r['repeat']==repeat and r['count']==n];med={mode:st.median(r['wall_ns']/1e6 for r in a if r['mode']==mode) for mode in ['ordinary','profiled']};profiles=[r['inventory'][0] for r in a if r['mode']=='profiled'];names=sorted(set().union(*(p['phase_ns'] for p in profiles)))
  summary.append(dict(repeat=repeat,count=n,launch_ms=med,instrumentation_delta_ms=med['profiled']-med['ordinary'],inventory_ms=st.median(p['wall_ns']/1e6 for p in profiles),exclusive_phase_ms={name:st.median(p['phase_ns'].get(name,0)/1e6 for p in profiles) for name in names},phase_calls={name:sorted(set(p['phase_calls'].get(name,0) for p in profiles)) for name in names}))
(O/'profile.json').write_text(json.dumps(dict(cpu=cpu,samples=len(samples),repeats=2,samples_per_cell=30,seed=655800,binaries={n:hashlib.sha256((W/n).read_bytes()).hexdigest() for n in ['reuse','profiled']},summary=summary,scope='exclusive per-invocation phases; independent includes Git/read/hash minus observation hooks; derivation includes selection, child file checks and cloning minus framing; other is inventory setup, root validation, observation copies and teardown; serialization and profile-file output occur outside phase clock but inside profiled process wall time'),indent=2)+'\n')
print(json.dumps(summary,indent=2))
