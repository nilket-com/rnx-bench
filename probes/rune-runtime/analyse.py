"""Fail-closed standing report; reproduction warnings stop attribution."""
import argparse,collections,hashlib,json,math,pathlib,statistics,subprocess
from suite import profile_valid
P=pathlib.Path(__file__).resolve().parent;ROOT=P.parents[1]
def analyse(out):
 def read(n):return json.loads((out/n).read_text())
 def stats(v):
  assert v and all(isinstance(x,(int,float)) and math.isfinite(x) and x>0 for x in v)
  s=sorted(v);return dict(n=len(v),median=statistics.median(v),minimum=min(v),maximum=max(v),p10=s[int((len(s)-1)*.1)],p90=s[int((len(s)-1)*.9)])
 subjects=read('subjects.json')
 def check_binary(v):
  if 'path' in v:
   assert hashlib.sha256(pathlib.Path(v['path']).read_bytes()).hexdigest()==v['sha256'],'binary changed '+v['path']
  else:
   for child in v.values():check_binary(child)
 check_binary(subjects['binaries'])
 for file,digest in subjects['metadata']['external_sources'].items():assert hashlib.sha256(pathlib.Path(file).read_bytes()).hexdigest()==digest,'external source changed '+file
 for file,digest in subjects['sources'].items():assert hashlib.sha256((P/file).read_bytes()).hexdigest()==digest,'source changed '+file
 clock=read('clock-preflight.json');assert set(clock)=={'true','cached'}
 for v in clock.values():
  stats(v['native_ns']);assert len(v['native_ns'])==50 and math.isfinite(v['reference_ns']) and v['reference_ns']>0
  assert v['passed'] is True and abs(statistics.median(v['native_ns'])-v['reference_ns'])<=150000
 cases=read('cases.json');assert len(cases)==36
 expected={(c['subject'],c['mode'],c['work']):c for c in cases};assert len(expected)==36
 rows=[json.loads(l) for l in (out/'samples.jsonl').read_text().splitlines()];assert len(rows)==2265,len(rows)
 groups=collections.defaultdict(list);seen=set()
 for r in rows:
  key=(r['subject'],r['mode'],r['work']);identifier=(*key,r['repeat'],r['sample']);assert identifier not in seen;seen.add(identifier)
  if r['mode']=='unpinned':assert r['repeat']==0 and r['sample'] in range(30) and len(r['affinity'])>1
  else:
   assert key in expected and r['repeat'] in range(3) and r['affinity']==[4]
   assert r['sample'] in range(5 if r['work'] in ('numeric','strings','fib') else 30)
  raw=out/r['raw'];assert raw.is_file() and raw.resolve().is_relative_to(out.resolve())
  capture=raw.read_text().splitlines();assert len(capture)==4 and capture[1]=='0' and not bytes.fromhex(capture[3])
  assert int(capture[0])==r['ns'] and r['ns']>0
  expected_text='42\n' if r['mode']=='unpinned' else expected[key]['expected']
  assert bytes.fromhex(capture[2])==expected_text.encode(),'retained stdout mismatch'
  groups[key].append(r['ns']/1e6)
 assert len(groups)==41
 for key,v in groups.items():assert len(v)==(30 if key[1]=='unpinned' else 15 if key[2] in ('numeric','strings','fib') else 90)
 baseline=json.loads(subprocess.check_output(['git','-C',str(ROOT),'show','20f9806:results/rune-base-0168/analysis.json']))
 warnings=[]
 for r in baseline['wall_ms']:
  if r['mode']=='unpinned':continue
  now=stats(groups[(r['base'],r['mode'],r['work'])]);limit=max(r['median']*.10,r['p90']-r['p10'])
  if abs(now['median']-r['median'])>limit:warnings.append(dict(base=r['base'],mode=r['mode'],work=r['work'],baseline=r['median'],now=now['median'],limit=limit))
 (out/'baseline-reproduction.json').write_text(json.dumps(dict(warnings=warnings,passed=not warnings),indent=2)+'\n')
 # A warning is a stop, not averaged away by another workload.
 assert not warnings,'STOP baseline reproduction warning; attribution not emitted'
 reused=read('reused-calls.json');assert len(reused)==18
 assert {(r['base'],r['work'],r['repeat']) for r in reused}=={(b,w,rep) for b in ('old','new') for w in ('answer','numeric','fib') for rep in range(3)}
 for r in reused:
  assert r['calls']==20;stats([r['process_ns'],r['context_ns'],r['runtime_cumulative_ns'],r['compile_cumulative_ns'],r['calls_ns']])
  assert r['context_ns']<=r['runtime_cumulative_ns']<=r['compile_cumulative_ns'] and r['process_ns']>r['calls_ns']
 diag=read('profile.json');plain=read('unmodified-context.json');assert len(diag)==12 and len(plain)==120
 for r in diag:assert len(r['rows'])==20;profile_valid(r['rows'],r['enabled'])
 overhead=read('profile-overhead.json')
 plainkeys={(r['repeat'],r['stdio'],r['iteration']) for r in plain};assert len(plainkeys)==120
 assert plainkeys=={(rep,stdio,i) for rep in range(3) for stdio in (False,True) for i in range(20)}
 for r in plain:stats([r['context_ns'],r['drop_ns']])
 assert {(r['repeat'],r['enabled'],r['stdio']) for r in diag}=={(rep,en,st) for rep in range(3) for en in (False,True) for st in (False,True)}
 a=statistics.median(r['context_ns'] for r in plain if r['stdio']);b=statistics.median(c['construct_ns'] for r in diag if r['enabled'] and r['stdio'] for c in r['rows'])
 assert overhead==dict(unmodified_median_ns=a,enabled_median_ns=b,ratio=b/a,passed=b/a<=1.20) and b/a<=1.20,'STOP diagnostic overhead'
 allocation_profile=read('profile-allocation.json');assert len(allocation_profile)==6
 assert {(r['repeat'],r['stdio']) for r in allocation_profile}=={(rep,st) for rep in range(3) for st in (False,True)}
 for r in allocation_profile:
  assert len(r['rows'])==20;profile_valid(r['rows'],True)
  assert all(v['allocation'] is not None for c in r['rows'] for v in c['rows'])
 by=collections.defaultdict(list);events=collections.defaultdict(list)
 for r in diag:
  if not r['enabled']:continue
  for c in r['rows']:
   for row in c['rows']:
    key=(r['stdio'],row['module'],row['phase']);by[key].append(row['ns']);events[key].append(row['events'])
 assert all(len(v)==60 for v in by.values())
 # Counter metadata has to agree with original raw perf values.
 counter=read('counters.json');assert len(counter)==84
 identities=set()
 for r in counter:
  key=(r['base'],r['mode'],r['work'],r['repeat']);assert key not in identities;identities.add(key)
  label=r['base']+'-'+r['mode']+('-'+r['work'] if r['work'] else '')+'-'+str(r['repeat'])+'.perf.jsonl'
  raw=[json.loads(l) for l in (out/label).read_text().splitlines()];assert len(raw)==2
  values={}
  for v in raw:
   event=next((e for e in ('instructions','cycles') if v['event'] in (e+':u','cpu_core/'+e+'/u')),None)
   assert event and event not in values and float(v['pcnt-running'])>=99 and float(v['event-runtime'])>0
   values[event]=float(v['counter-value']);assert math.isfinite(values[event]) and values[event]>0
  assert values==r['counts'] and r['status']==0 and r['disabled_ns']>r['enabled_ns']
  key=(r['base'],'run',r['work']);expect=expected.get(key,{}).get('expected','')
  if r['mode'] in ('floor','empty-context','context','runtime','compile'):expect=''
  if r['mode']=='reuse':expect*=20
  assert r['stdout']==expect
 from counters_contract import identities as counter_cases,expected_output
 assert identities=={(*key,rep) for key in counter_cases() for rep in range(3)}
 for name in ('allocations.json','rss.json'):
  data=read(name);assert len(data)==28
  keys={(r['base'],r['mode'],r['work']) for r in data};assert keys==counter_cases() and len(keys)==28
  for r in data:
   assert r['stdout']==expected_output(r['mode'],r['work'])
   if name=='allocations.json':
    import ast
    v=ast.literal_eval(r['stderr'].splitlines()[-1].removeprefix('ALLOC '))
    assert list(v)==[r[n] for n in ('calls','allocated_bytes','live_bytes','peak_bytes')]
    assert all(type(n) is int and n>=0 for n in v) and v[3]>=v[2]
   else:assert type(r['maxrss_kib']) is int and r['maxrss_kib']>0
 module_totals=collections.defaultdict(list);stage_totals=collections.defaultdict(list)
 for r in diag:
  if not r['enabled']:continue
  for context in r['rows']:
   modules=collections.defaultdict(dict);stages=collections.defaultdict(int)
   for row in context['rows']:
    modules[row['module']][row['phase']]=row['ns']
    if row['phase'] not in ('module-construction','install'):stages[row['phase']]+=row['ns']
   for module,values in modules.items():module_totals[(r['stdio'],module)].append(values['module-construction']+values['install'])
   for phase,ns in stages.items():stage_totals[(r['stdio'],phase)].append(ns)
 report=dict(modules=[dict(stdio=k[0],module=k[1],**stats(v)) for k,v in module_totals.items()],stages=[dict(stdio=k[0],stage=k[1],**stats(v)) for k,v in stage_totals.items()],reused_calls=reused,wall_ms=[dict(subject=k[0],mode=k[1],work=k[2],**stats(v)) for k,v in sorted(groups.items(),key=str)],profile=[dict(stdio=k[0],module=k[1],phase=k[2],**stats(v),event_vectors=events[k]) for k,v in sorted(by.items())])
 (out/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
 lines=['# Standing runtime baseline (0169)','', '| Subject | Mode / workload | Median ms | p10–p90 ms |', '|---|---|---:|---:|']
 for r in report['wall_ms']:lines.append(f"| {r['subject']} | {r['mode']} {r['work'] or ''} | {r['median']:.3f} | {r['p10']:.3f}–{r['p90']:.3f} |")
 for stdio in (False,True):
  lines+=['',f'## Complete registration diagnostic: stdio={stdio}','', '| Module (construction + install, paired) | Median ms |','|---|---:|']
  for row in sorted((r for r in report['modules'] if r['stdio']==stdio),key=lambda r:-r['median'])[:10]:lines.append(f"| {row['module']} | {row['median']/1e6:.3f} |")
  lines+=['','| Install stage (summed across modules per context) | Median ms |','|---|---:|']
  for row in sorted((r for r in report['stages'] if r['stdio']==stdio),key=lambda r:-r['median']):lines.append(f"| {row['stage']} | {row['median']/1e6:.3f} |")
 lines+=['','Diagnostic timings are separate, with complete module/stage hierarchy and overhead in JSON. Nested event counts do not add to parent event counts. No optimization chosen.','']
 (out/'REPORT.md').write_text('\n'.join(lines))
 print('PASS: 2265 primary samples, 84 counter windows, 34-module diagnostic coverage; baseline reproduced')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);analyse(p.parse_args().out)
