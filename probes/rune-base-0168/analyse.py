"""Fail closed over retained measurement counts, outputs and counter windows."""
import collections, hashlib, json, pathlib, re, statistics
P = pathlib.Path(__file__).resolve().parent
O = P.parents[1] / 'results/rune-base-0168'
def read(name): return json.loads((O / name).read_text())
def stats(values):
 assert values and all(x > 0 for x in values)
 return dict(n=len(values), median=statistics.median(values), minimum=min(values), maximum=max(values), p10=sorted(values)[int((len(values)-1)*.1)],p90=sorted(values)[int((len(values)-1)*.9)])
samples = [json.loads(x) for x in (O/'samples.jsonl').read_text().splitlines()]
assert len(samples) == 1410
checks = {(r['base'],r['mode'],r['work']):r['expected'] for r in read('measurement-validation.json')}
assert len(checks) == 20
by=collections.defaultdict(list);seen=set()
for r in samples:
 key=(r['base'],r['mode'],r['work']); identity=(*key,r['repeat'],r['sample']);assert identity not in seen;seen.add(identity)
 assert r['ns'] > 0
 count=5 if r['work'] in ('numeric','strings','fib') else 30
 if r['mode']=='unpinned':assert r['repeat']==0 and r['affinity']==read('conditions.json')['original_affinity']
 else:assert key in checks and r['repeat'] in range(3) and r['affinity']==[4]
 assert r['sample'] in range(count)
 by[key].append(r['ns']/1e6)
assert len(by)==22
for (base,mode,work),v in by.items():assert len(v)==(30 if mode=='unpinned' else 15 if work in ('numeric','strings','fib') else 90)
assert all(r['passed'] for r in read('clock-preflight.json').values())
wall=[dict(base=k[0],mode=k[1],work=k[2],**stats(v)) for k,v in sorted(by.items(),key=str)]
def output(r):
 mode=r['mode'];work=r['work']; expected=checks.get((r['base'],'run',work),'')
 if mode in ('compile','floor','context','empty-context','runtime','registration'): expected=''
 elif mode=='reuse':expected*=20
 assert r['stdout']==expected,(r['base'],mode,work)
 if 'status' in r: assert r['status']==0
counter=collections.defaultdict(lambda:collections.defaultdict(list))
rows=read('counters.json');assert len(rows)==90
identities=set()
for r in rows:
 identity=(r['base'],r['mode'],r['work'],r['repeat']);assert identity not in identities and r['repeat'] in range(3);identities.add(identity)
 output(r);assert r['disabled_ns']>r['enabled_ns'];k=(r['base'],r['mode'],r['work'])
 raw=[json.loads(x) for x in (O/(f"{r['base']}-{r['mode']}"+(f"-{r['work']}" if r['work'] else '')+f"-{r['repeat']}.perf.jsonl")).read_text().splitlines()]
 assert len(raw)==2
 raw_counts={}
 for item in raw:
  assert float(item['pcnt-running'])>=99 and float(item['event-runtime'])>0
  event=next((e for e in ('instructions','cycles') if item['event'] in (e+':u','cpu_core/'+e+'/u')),None)
  assert event is not None and event not in raw_counts;raw_counts[event]=float(item['counter-value'])
 assert raw_counts==r['counts']
 for event in ('instructions','cycles'):assert r['counts'][event]>0;counter[k][event].append(r['counts'][event])
assert len(counter)==30 and all(len(v['instructions'])==3 for v in counter.values())
cs=[dict(base=k[0],mode=k[1],work=k[2],**{e:stats(v) for e,v in events.items()}) for k,events in sorted(counter.items(),key=str)]
for name in ('allocations.json','rss.json'):
 rows=read(name);assert len(rows)==30
 identities=set()
 for r in rows:
  identity=(r['base'],r['mode'],r['work']);assert identity not in identities;identities.add(identity);output(r)
 assert identities==set(counter)
phases=[]; modules=[]
for r in read('inprocess.json'):
 output(r)
 if r['mode']=='registration':
  lines=[s.split() for s in r['stderr'].splitlines() if s.startswith('MODULE ')]
  assert len(lines)==(30 if r['base']=='old' else 31)
  modules.append(dict(base=r['base'],repeat=r['repeat'],construction_ns=sum(int(s[2]) for s in lines),install_ns=sum(int(s[3]) for s in lines),drop_ns=int(re.search(r'REGDROP (\d+)',r['stderr'])[1])))
 else:
  m=re.fullmatch(r'PHASES (\d+) (\d+) (\d+) (\d+) (\d+)\n',r['stderr']);assert m
  c,rt,comp,call,n=map(int,m.groups());assert c<=rt<=comp and n==(20 if r['mode']=='reuse' else 1)
  phases.append(dict(base=r['base'],mode=r['mode'],work=r['work'],repeat=r['repeat'],context_ns=c,runtime_ns=rt-c,compile_ns=comp-rt,call_ns=call/n,calls=n))
correct=read('correctness.json');assert len(correct)==26 and all(r['passed'] for r in correct)
for name in {r['name'] for r in correct}:
 pair=[r for r in correct if r['name']==name];assert len(pair)==2
 assert pair[0]['outcome']==pair[1]['outcome']
 assert pair[0].get('semantic_error')==pair[1].get('semantic_error') and pair[0]['stdout']==pair[1]['stdout']
robust=read('robustness.json');assert len(robust['rows'])==18
# Runtime/compiler source and fixture bytes used by the timed binaries must remain intact.
for path,digest in read('conditions.json')['sources'].items():
 if path.endswith('.rs') or '/fixtures/' in '/'+path or path.endswith(('Cargo.toml','Cargo.lock')):
  assert hashlib.sha256((P/path).read_bytes()).hexdigest()==digest,path
result=dict(wall_ms=wall,counters=cs,phases_ns=phases,public_module_subset_ns=modules,allocation=read('allocations.json'),rss=read('rss.json'),correctness_rows=26,robustness=robust)
(O/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
lines=['# Rune base comparison (0168)','', '| Whole-process mode | 0.14.2 median ms (min–max) | main median ms (min–max) | main/old |','|---|---:|---:|---:|']
for mode,work in [('floor',None),('empty-context',None),('context',None),('runtime',None),('compile','answer'),('run','empty'),('run','answer'),('run','numeric'),('run','strings'),('run','fib'),('unpinned','answer')]:
 a,b=[stats(by[(base,mode,work)]) for base in ('old','new')]
 label=mode+(' '+work if work else '')
 lines.append(f"| {label} | {a['median']:.3f} ({a['minimum']:.3f}–{a['maximum']:.3f}) | {b['median']:.3f} ({b['minimum']:.3f}–{b['maximum']:.3f}) | {b['median']/a['median']:.3f} |")
lines += ['', 'Counter windows exclude startup, pipe waiting and teardown; these are separate binaries with allocation accounting disabled.', '', '| Mode | old instructions | main instructions | main/old |', '|---|---:|---:|---:|']
for mode,work in [('context',None),('runtime',None),('compile','answer'),('run','answer'),('run','numeric'),('run','strings'),('run','fib')]:
 a,b=[statistics.median(counter[(base,mode,work)]['instructions']) for base in ('old','new')]
 lines.append(f'| {mode} {work or ""} | {a:,.0f} | {b:,.0f} | {b/a:.3f} |')
lines += ['', 'All raw values and dispersion are in analysis.json. No samples removed. Unpinned 42 was measured later, separately. These are harnesses, not stock rnx startup measurements.', '']
(O/'TABLES.md').write_text('\n'.join(lines))
print('PASS: 1410 timed samples, 90 counter windows, 30 allocation / 30 RSS observations, 26 correctness rows, 18 robustness rows')
