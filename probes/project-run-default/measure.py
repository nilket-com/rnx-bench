"""Everyday product launch, full verification, and explicit transition costs."""
from pathlib import Path
import json,os,random,statistics,subprocess,time,tempfile,hashlib,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/project-run-default-0059';P=B/'probes/polars-cost/target/project';T=R/'tools/project/target/release/rnx-project';OLD=B/'probes/project-run-stage/target/before';STAGE=H/'target/stage-one';PROFILE=H/'target/profile/target/release/rnx-project'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_','POLARS_'))};ENV.update(TERM='xterm',NO_COLOR='1',POLARS_MAX_THREADS='1',RNX_CONFIG=str(H/'target/absent'),RNX_HISTORY=str(H/'target/history'))
for op in ['lock','build']:
 with (O/(op+'.log')).open('w') as f:subprocess.run([T,op,'--manifest',P/'rnx.toml','--offline'],env=ENV,stdout=f,stderr=subprocess.STDOUT,check=True)
receipt=P/'.rnx/receipt.json';r=json.loads(receipt.read_text());assert r['format']==2
v2=receipt.read_bytes();v1=json.dumps({k:r[k] for k in ['lock_sha256','executable_sha256']}|{'format':1}).encode();EXE=P/'.rnx/artifacts'/r['executable_sha256'];MAP=next((P/'.rnx/maps').glob('*.json'))
CPU=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{CPU})
base=['run','--manifest',str(P/'rnx.toml')];cmds={'old':[str(OLD),*base,'--'],'stage-one':[str(STAGE),*base,'--'],'default':[str(T),*base,'--'],'verify':[str(T),*base,'--verify','--'],'direct':[str(EXE),'run','--source-map',str(MAP),str(P/'main.rn')]}
expected={'init':'ready\n','pipeline':'DataFrame: 2 rows × 2 columns\n"category": string | "total": i64\n"a" | 2\n"🦀" | 7\n\n'}
def launch(command,mode,profile=False):
 with tempfile.TemporaryDirectory(prefix='rnx-default-launch-') as tmp:
  start=time.perf_counter_ns();p=subprocess.run(command+[mode,tmp],env=ENV,capture_output=True,text=True,timeout=30);ms=(time.perf_counter_ns()-start)/1e6
  assert p.returncode==0 and p.stdout==expected[mode],(p.returncode,p.stdout,p.stderr)
  if profile:
   assert p.stderr.startswith('INVENTORY ') and p.stderr.count('\n')==1;pairs=json.loads(p.stderr.removeprefix('INVENTORY '));groups={}
   for k,v in pairs:groups[k]=groups.get(k,0)+v
   return ms,groups
  assert not p.stderr,p.stderr
  return ms
for k in cmds:
 for m in expected:receipt.write_bytes(v1 if k in ['old','stage-one'] else v2);launch(cmds[k],m)
rows=[];(O/'journal.jsonl').write_text('')
for repeat in range(2):
 for n in range(20):
  jobs=[(k,m) for k in cmds for m in expected];random.Random(59200+repeat*100+n).shuffle(jobs)
  for k,m in jobs:
   # Old tools require v1; current tools receive the same valid v2 stamp.
   # Receipt preparation is outside timing and affects no public/source input.
   receipt.write_bytes(v1 if k in ['old','stage-one'] else v2)
   x={'repeat':repeat,'sample':n,'kind':k,'mode':m,'ms':launch(cmds[k],m)};rows.append(x)
   with (O/'journal.jsonl').open('a') as f:f.write(json.dumps(x)+'\n')
 print('repeat',repeat,'complete',flush=True)
summary={m:{k:[statistics.median(x['ms'] for x in rows if x['kind']==k and x['mode']==m and x['repeat']==r) for r in range(2)] for k in cmds} for m in expected}
(O/'samples.json').write_text(json.dumps(rows,indent=2)+'\n');(O/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
# Migration and metadata mismatch are separately timed, never hidden as warm defaults.
transitions=[];st=EXE.stat()
try:
 for n in range(5):
  receipt.write_bytes(v1);transitions.append({'kind':'legacy-migration','sample':n,'ms':launch(cmds['default'],'pipeline')});assert json.loads(receipt.read_text())['format']==2
  receipt.write_bytes(v2);os.utime(EXE,ns=(st.st_atime_ns,st.st_mtime_ns+(n+1)*1_000_000_000));transitions.append({'kind':'metadata-mismatch','sample':n,'ms':launch(cmds['default'],'pipeline')})
  os.utime(EXE,ns=(st.st_atime_ns,st.st_mtime_ns));receipt.write_bytes(v2)
finally:os.utime(EXE,ns=(st.st_atime_ns,st.st_mtime_ns));receipt.write_bytes(v2)
# No native inventory is declared for the explicit prebuilt-executable override.
with tempfile.TemporaryDirectory(prefix='rnx-override-cost-') as tmp:
 q=Path(tmp);shutil.copy2(P/'main.rn',q/'main.rn');(q/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[executable]\npath='+json.dumps(str(EXE))+'\n')
 p=subprocess.run([T,'lock','--manifest',q/'rnx.toml'],env=ENV,capture_output=True,text=True,timeout=30);assert p.returncode==0,p.stderr
 for n in range(5):
  (q/'.rnx/receipt.json').unlink(missing_ok=True);transitions.append({'kind':'override-establishment','sample':n,'ms':launch([str(T),'run','--manifest',str(q/'rnx.toml'),'--'],'pipeline')})
(O/'transitions.json').write_text(json.dumps(transitions,indent=2)+'\n')
profiles=[]
for n in range(20):
 receipt.write_bytes(v2)
 for kind in (['profile','control'] if n%2==0 else ['control','profile']):
  if kind=='profile':ms,groups=launch([str(PROFILE),*base,'--'],'init',True)
  else:ms=launch(cmds['default'],'init');groups={}
  profiles.append({'sample':n,'kind':kind,'ms':ms,'groups':groups})
(O/'inventory-samples.json').write_text(json.dumps(profiles,indent=2)+'\n')
keys=next(x['groups'].keys() for x in profiles if x['groups']);subdivision={k:statistics.median(x['groups'][k] for x in profiles if x['kind']=='profile') for k in keys}
subdivision['profile_total']=statistics.median(x['ms'] for x in profiles if x['kind']=='profile');subdivision['control_total']=statistics.median(x['ms'] for x in profiles if x['kind']=='control')
(O/'inventory-summary.json').write_text(json.dumps(subdivision,indent=2)+'\n')
conditions={'cpu':CPU,'polars_threads':1,'samples_per_repeat_cell':20,'repeats':2,'seed':59200,'commands':cmds,'timer':'perf_counter_ns no-shell spawn/capture/wait; fresh output dirs and receipt preparation outside timing','cache':'warm, both modes warmed; all 400 samples retained','receipt_controls':'old/stage-one get v1, current default/verify get valid v2; same lock/artifact/source inputs','binaries':{k:{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for k,p in [('old',OLD),('stage-one',STAGE),('after',T),('artifact',EXE),('profile',PROFILE)]},'rustc':subprocess.check_output(['rustc','-Vv'],text=True)}
(O/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
for name in ['rnx.lock','rnx.Cargo.lock']:(O/name).write_bytes((P/name).read_bytes())
print(json.dumps({'launch':summary,'inventory':subdivision},indent=2),flush=True)
for i in range(2):
 assert summary['pipeline']['default'][i] <= summary['pipeline']['old'][i]*.30,'70% gate failed'
 assert summary['pipeline']['default'][i]-summary['pipeline']['direct'][i]<=25,'25ms gate failed'
