from common import *
import random,statistics as st
rows=[r for r in json.loads((O/'roster.json').read_text()) if r['kind']=='git'];env=json.loads((O/'roster-env.json').read_text());cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu});phase=O/'phases.jsonl';assert not phase.exists();samples=[];phases=[]
for repeat in range(2):
 jobs=[(r,kind,n) for r in rows for kind in ['stock','profile-control','profiled'] for n in range(30)];random.Random(675300+repeat).shuffle(jobs)
 for row,kind,n in jobs:
  args=[T/kind,*(['project'] if kind=='stock' else []),'eval','--manifest',row['manifest'],'--','42'];start=time.perf_counter_ns();p=subprocess.run(list(map(str,args)),cwd=T,env=env|({'RNX_GATE_PROFILE':str(phase)} if kind=='profiled' else {}),capture_output=True,timeout=15);ns=time.perf_counter_ns()-start;assert p.returncode==0 and p.stdout==b'42\n' and not p.stderr
  sample={'repeat':repeat,'count':row['count'],'kind':kind,'sample':n,'ns':ns};samples.append(sample)
  if kind=='profiled':
   v=json.loads(phase.read_text().splitlines()[-1]);assert sum(v[k] for k in ['read_lock_ns','inputs_ns','artifact_ns','command_ns'])==v['total_ns'];phases.append(sample|v)
save('profile-samples.json',samples);save('profile-phases.json',phases)
summary=[]
for count in range(4):
 for repeat in range(2):
  med={k:st.median(s['ns']/1e6 for s in samples if s['kind']==k and s['repeat']==repeat and s['count']==count) for k in ['stock','profile-control','profiled']}
  summary.append({'count':count,'repeat':repeat,'whole_process_ms':med,'phases_ms':{k:st.median(s[k]/1e6 for s in phases if s['repeat']==repeat and s['count']==count) for k in ['read_lock_ns','inputs_ns','artifact_ns','command_ns','total_ns']}})
save('profile-summary.json',summary);save('profile-conditions.json',{'cpu':cpu,'source':'1b894e0 plus archived profile.patch','samples':len(samples),'scope':'isolated standalone management control/profiler; all product headline samples use uninstrumented stock rnx','note':'phase intervals are disjoint; medians need not add; total begins at git_launch, excluding CLI dispatch, Project::open and new_lock envelope read'})
print('profiling complete',flush=True)
