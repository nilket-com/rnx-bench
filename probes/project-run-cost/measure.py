"""Paired instrumented/control launches; no verification skipped."""
from pathlib import Path
import json,os,random,statistics,subprocess,time,tempfile,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/project-run-cost-0059'
P=B/'probes/polars-cost/target/project';T=R/'tools/project/target/release/rnx-project';I=H/'target/instrumented/target/release/rnx-project'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_','POLARS_'))};ENV.update(TERM='xterm',NO_COLOR='1',POLARS_MAX_THREADS='1',RNX_CONFIG=str(H/'target/absent'),RNX_HISTORY=str(H/'target/history'))
# Reuse the accepted Polars project/cache; rebuild identities after evidence edits.
for op in ['lock','build']:
 with (O/(op+'.log')).open('w') as f:subprocess.run([T,op,'--manifest',P/'rnx.toml','--offline'],env=ENV,stdout=f,stderr=subprocess.STDOUT,check=True)
a=json.loads((P/'.rnx/receipt.json').read_text());EXE=P/'.rnx/artifacts'/a['executable_sha256'];MAP=next((P/'.rnx/maps').glob('*.json'))
CPU=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{CPU})
cmds={'stock':[str(T),'run','--manifest',str(P/'rnx.toml'),'--'],'profile':[str(I),'run','--manifest',str(P/'rnx.toml'),'--'],'direct':[str(EXE),'run','--source-map',str(MAP),str(P/'main.rn')]}
expected={'init':'ready\n','pipeline':'DataFrame: 2 rows × 2 columns\n"category": string | "total": i64\n"a" | 2\n"🦀" | 7\n\n'}
def run(kind,mode):
 with tempfile.TemporaryDirectory(prefix='rnx-launch-breakdown-') as tmp:
  start=time.perf_counter_ns();p=subprocess.run(cmds[kind]+[mode,tmp],env=ENV,capture_output=True,text=True,timeout=30);ms=(time.perf_counter_ns()-start)/1e6
  assert p.returncode==0 and p.stdout==expected[mode],(kind,p.returncode,p.stdout,p.stderr)
  if kind=='profile':
   assert p.stderr.startswith('PROFILE ') and p.stderr.count('\n')==1,p.stderr
   phases=dict(json.loads(p.stderr.removeprefix('PROFILE ')))
  else:assert not p.stderr;phases={}
  return {'kind':kind,'mode':mode,'ms':ms,'phases_ms':phases}
for k in cmds:
 for m in expected:run(k,m)
rows=[];(O/'journal.jsonl').write_text('')
for repeat in range(2):
 for n in range(20):
  jobs=[(k,m) for k in cmds for m in expected];random.Random(59000+repeat*100+n).shuffle(jobs)
  for k,m in jobs:
   row=dict(run(k,m),repeat=repeat,sample=n);rows.append(row)
   with (O/'journal.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 print('repeat',repeat,'complete',flush=True)
(O/'samples.json').write_text(json.dumps(rows,indent=2)+'\n')
summary={m:{k:[statistics.median(x['ms'] for x in rows if x['kind']==k and x['mode']==m and x['repeat']==r) for r in range(2)] for k in cmds} for m in expected}
phases={m:{key:[statistics.median(x['phases_ms'][key] for x in rows if x['kind']=='profile' and x['mode']==m and x['repeat']==r) for r in range(2)] for key in rows[next(i for i,x in enumerate(rows) if x['kind']=='profile')]['phases_ms']} for m in expected}
(O/'summary.json').write_text(json.dumps({'launch_ms':summary,'phases_ms':phases},indent=2)+'\n')
(O/'conditions.json').write_text(json.dumps({'cpu':CPU,'threads':1,'samples_per_cell_repeat':20,'repeats':2,'commands':cmds,'artifact_bytes':EXE.stat().st_size,'artifact_sha256':hashlib.sha256(EXE.read_bytes()).hexdigest(),'stock_tool_sha256':hashlib.sha256(T.read_bytes()).hexdigest(),'timer':'Instant around disjoint check groups; one JSON emission before exec; external perf_counter_ns around spawn/capture/wait','cache':'warm, pinned same CPU as gate5; no measurements discarded'},indent=2)+'\n')
print(json.dumps({'launch_ms':summary,'phases_ms':phases},indent=2),flush=True)
