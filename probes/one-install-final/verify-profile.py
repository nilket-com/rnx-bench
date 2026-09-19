from common import *
import statistics as st
row=next(r for r in json.loads((O/'roster.json').read_text()) if r['kind']=='git' and r['count']==1);env=json.loads((O/'roster-env.json').read_text());cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu});phase=O/'verify-phases.jsonl';assert not phase.exists();samples=[]
for n in range(10):
 start=time.perf_counter_ns();p=subprocess.run([str(T/'profiled'),'eval','--manifest',row['manifest'],'--verify','--','42'],env=env|{'RNX_GATE_PROFILE':str(phase)},cwd=T,capture_output=True,timeout=15);ns=time.perf_counter_ns()-start;assert p.returncode==0 and p.stdout==b'42\n' and not p.stderr
 v=json.loads(phase.read_text().splitlines()[-1]);assert sum(v[k] for k in ['read_lock_ns','inputs_ns','artifact_ns','command_ns'])==v['total_ns'];samples.append(v|{'wall_ns':ns,'sample':n})
save('verify-profile.json',{'cpu':cpu,'samples':samples,'median_ms':{k:st.median(s[k]/1e6 for s in samples) for k in samples[0] if k.endswith('_ns')},'scope':'diagnostic attribution only; headline verify remains the ordinary product measurement'})
