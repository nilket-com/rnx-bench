"""Correctness precedes deciding observations; primary and diagnostic results separate."""
import collections,math,json,os,pathlib,random,statistics,subprocess,sys,time
P=pathlib.Path(__file__).resolve().parent;ROOT=P.parents[1];F=P/'fixtures'
def write(out,name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n')
def subjects(out):return json.loads((out/'subjects.json').read_text())['binaries']
def engine(s,base,mode,work=None,kind='primary'):
 return [s[base][kind]['path'],mode,*([str(F/(work+'.rn'))] if work else [])]
def profile(s,enabled,stdio,repeats=1,kind='primary',fixture=None):
 return [s['profile'][kind]['path'],'enabled' if enabled else 'disabled','true' if stdio else 'false',str(repeats),*([str(F/(fixture+'.rn'))] if fixture else [])]
def parsed(stderr):return [json.loads(x) for x in stderr.decode().splitlines()]
def profile_valid(rows,enabled):
 modules=json.loads((P/'expected_modules.json').read_text());phases=['module','types','traits','items','associated','trait_impls','reexports','construct']
 for i,r in enumerate(rows):
  assert r['iteration']==i and r['enabled']==enabled and math.isfinite(r['construct_ns']) and r['construct_ns']>0 and math.isfinite(r['drop_ns']) and r['drop_ns']>0
  if i==0:assert r['inventory'] and 'defaults:true' in r['inventory']
  if enabled:
   want=[(m,p) for m in modules for p in ['module-construction']+phases+['install']]
   got=[(v['module'],v['phase']) for v in r['rows']]
   assert got==want,(len(got),len(want),'incomplete module/stage coverage')
   for m in modules:
    v=[v for v in r['rows'] if v['module']==m]
    assert sum(q['ns'] for q in v if q['phase'] in phases)<=next(q['ns'] for q in v if q['phase']=='install'),'stage hierarchy invalid'
   assert all(math.isfinite(v['ns']) and v['ns']>0 and len(v['events'])==3 and all(type(n) is int and n>=0 for n in v['events']) for v in r['rows'])
   for v in r['rows']:
    if v['allocation'] is not None:
     assert len(v['allocation'])==5 and all(type(n) is int and n>=0 for n in v['allocation'])
  else:assert not r['rows']
def controls(j,out):
 # Limits apply to robustness children as inherited process limits, core dumps off.
 import resource
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 s=subjects(out);records=[]
 for base in ('old','new'):
  for name,expected,mode in [('int-boundaries',b'9223372036854775807\n-9223372036854775808\n','run'),('floats',b'0.75\n3.0\n','run'),('unicode','7\na🦀é\n'.encode(),'run'),('vec-alias',b'2\n','run'),('object-alias',b'2\n','run'),('closure',b'42\n','run'),('iterator-trait',b'12\n','run'),('async',b'42\n','async')]:
   j.run(engine(s,base,mode,name),base+'-'+name,expected=expected)
   records.append(dict(base=base,name=name,status='PASS'))
  j.run(engine(s,base,'run','collections'),base+'-collections',expected=b'42\n1\n5\n')
  for name,error in [('sum-untyped','MissingInstanceFunction'),('overflow','Overflow'),('divide-zero','DivideByZero'),('undefined','MissingLocal'),('budget','Limited')]:
   cmd=engine(s,base,'run',name)+(['100'] if name=='budget' else [])
   status,so,se=j.run(cmd,base+'-'+name,allowed=(1,));assert not so and error.encode() in se
   records.append(dict(base=base,name=name,status='PASS',semantic_error=error))
  for kind,depths in [('recursion',[10000,100000,1000000]),('expression',[100,1000,10000]),('literal',[100,1000,10000])]:
   for depth in depths:
    work=kind+'-'+str(depth);expected=(str(depth)+'\n').encode() if kind=='recursion' else b'1\n'
    status,so,se=j.run(engine(s,base,'run',work),base+'-'+work,deadline=10,allowed=(0,-6),limits=True)
    if base=='old' and kind!='recursion' and depth==10000:assert status==-6 and b'overflowed its stack' in se
    else:assert status==0 and so==expected and not se
    records.append(dict(base=base,name=work,status=status))
 # Diagnostic enabled/disabled execute the same controls through their own real Context.
 inventories={}
 for enabled in (False,True):
  for stdio in (False,True):
   _,so,se=j.run(profile(s,enabled,stdio),f'profile-{enabled}-{stdio}');assert not so
   rows=parsed(se);profile_valid(rows,enabled);inventories[(enabled,stdio)]=rows[0]['inventory']
  # Every fixture in the baseline corpus is checked in both diagnostic modes.
  for fixture in sorted(F.glob('*.rn')):
   name=fixture.stem
   errors={'sum-untyped':'MissingInstanceFunction','overflow':'Overflow','divide-zero':'DivideByZero','undefined':'MissingLocal','budget':'Limited'}
   command=profile(s,enabled,True,fixture=name)+(['100'] if name=='budget' else [])
   if name in errors:
    _,so,se=j.run(command,'profile-error-'+name,allowed=(1,));assert not so and errors[name].encode() in se
   else:
    _,so,se=j.run(command,'profile-corpus-'+name,deadline=10,limits=True)
    _,expected,primaryerr=j.run(engine(s,'new','async' if name=='async' else 'run',name),'profile-primary-oracle-'+name,deadline=10,limits=True)
    assert not primaryerr and so==expected;profile_valid(parsed(se),enabled)

 for stdio in (False,True):assert inventories[(False,stdio)]==inventories[(True,stdio)]
 write(out,'correctness.json',records);write(out,'inventory.json',{str(k):v for k,v in inventories.items()})
 # Corruption controls for diagnostic report coverage and parent/child intervals.
 _,so,se=j.run(profile(s,True,True),'profile-corruption-source');good=parsed(se);profile_valid(good,True)
 corrupt=[]
 for change in ('private-missing','duplicate-stage','inventory-flag','negative-clock','non-finite-clock','sum-exceeds-parent'):
  data=json.loads(json.dumps(good));r=data[0]
  if change=='private-missing':r['rows']=[v for v in r['rows'] if v['module']!='collections::hash_map']
  elif change=='duplicate-stage':r['rows'].append(r['rows'][0])
  elif change=='inventory-flag':r['inventory'].remove('defaults:true')
  elif change=='negative-clock':r['rows'][0]['ns']=-1
  elif change=='non-finite-clock':r['rows'][0]['ns']=float('inf')
  else:r['rows'][1]['ns']=r['construct_ns']*100
  try:profile_valid(data,True)
  except AssertionError:corrupt.append(change)
  else:raise RuntimeError('corruption accepted '+change)
 _,so,se=j.run(profile(s,True,True,kind='negative'),'actual-private-omission');assert not so
 assert parsed(se)[0]['inventory']!=good[0]['inventory'],'omission did not change inventory'
 try:profile_valid(parsed(se),True)
 except AssertionError:corrupt.append('actual-private-module-omission')
 else:raise RuntimeError('actual omitted module accepted')
 _,so,se=j.run(profile(s,True,True,kind='negative',fixture='collections'),'omitted-collection-capability',allowed=(1,));assert b'MissingItem' in se or b'MissingType' in se
 write(out,'profile-controls.json',corrupt)
def measure(j,out):
 s=subjects(out);original=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,{4})
 clock=P/'target/clock'
 def timed(cmd,expected,label):
  _,so,se=j.run([clock,'1',str(len(cmd)),*cmd],label,deadline=30);assert not se
  lines=so.decode().splitlines();assert len(lines)==4 and lines[1]=='0'
  ns=int(lines[0]);assert ns>0 and bytes.fromhex(lines[2])==expected and not bytes.fromhex(lines[3])
  return ns
 pre={}
 for name,cmd,expected in [('true',['/bin/true'],b''),('cached',[str(P/'target/cached')],b'42\n')]:
  f=out/(name+'-hyperfine.json');j.run(['hyperfine','-N','--warmup','5','--runs','50','--export-json',f,*cmd],'clock-'+name,deadline=60)
  native=[timed(cmd,expected,'clock-'+name) for _ in range(55)][5:]
  ref=statistics.median(json.loads(f.read_text())['results'][0]['times'])*1e9;med=statistics.median(native)
  pre[name]=dict(native_ns=native,reference_ns=ref,passed=abs(med-ref)<=150000)
 write(out,'clock-preflight.json',pre);assert all(r['passed'] for r in pre.values()),'STOP clock gate'
 expected={}
 for work in ('empty','answer','numeric','strings','fib'):
  _,so,se=j.run([sys.executable,ROOT/'probes/lua-rust-0001'/(work+'.py')],'oracle-'+work);assert not se;expected[work]=so
 cases=[]
 for base in ('old','new'):
  for mode in ('floor','empty-context','context','runtime'):cases.append(dict(subject=base,mode=mode,work=None,command=engine(s,base,mode),expected=''))
  cases.append(dict(subject=base,mode='compile',work='answer',command=engine(s,base,'compile','answer'),expected=''))
  for work,expect in expected.items():cases.append(dict(subject=base,mode='run',work=work,command=engine(s,base,'run',work),expected=expect.decode()))
 cases.append(dict(subject='stock',mode='eval',work='literal-42',command=[s['stock']['path'],'eval','42'],expected='42\n'))
 for work,expect in expected.items():
  cases.append(dict(subject='stock',mode='run',work=work,command=[s['stock']['path'],'run','--budget','1000000000',str(F/(work+'.rn'))],expected=expect.decode()))
  for lua in ('lua54','luajit'):
   cases.append(dict(subject=lua,mode='run',work=work,command=[s['lua'][lua]['path'],str(ROOT/'probes/lua-rust-0001'/(work+'.lua'))],expected=expect.decode()))
 assert len(cases)==36
 write(out,'cases.json',cases)
 for c in cases:
  for _ in range(2 if c['work'] in ('numeric','strings','fib') else 5):timed(c['command'],c['expected'].encode(),'warmup-'+c['subject'])
 with (out/'samples.jsonl').open('w') as f:
  for repeat in range(3):
   tasks=[(c,i) for c in cases for i in range(5 if c['work'] in ('numeric','strings','fib') else 30)];random.Random(16900+repeat).shuffle(tasks)
   for c,i in tasks:
    ns=timed(c['command'],c['expected'].encode(),'timed-'+c['subject'])
    f.write(json.dumps(dict(subject=c['subject'],mode=c['mode'],work=c['work'],repeat=repeat,sample=i,ns=ns,affinity=[4],raw=str((j.out/(f'{j.serial:05d}-timed-'+c['subject']+'.stdout')).relative_to(out))))+'\n');f.flush()
  os.sched_setaffinity(0,original)
  for subject in ('old','new','stock','lua54','luajit'):
   c=next(c for c in cases if c['subject']==subject and (c['work']=='answer' if subject!='stock' else c['mode']=='eval'))
   for i in range(30):
    ns=timed(c['command'],c['expected'].encode(),'unpinned-'+subject);f.write(json.dumps(dict(subject=subject,mode='unpinned',work=c['work'],repeat=0,sample=i,ns=ns,affinity=original,raw=str((j.out/(f'{j.serial:05d}-unpinned-'+subject+'.stdout')).relative_to(out))))+'\n');f.flush()
 os.sched_setaffinity(0,{4})
 # Primary reused calls: three processes, 20 checked outputs and per-call intervals each.
 reused=[]
 for base in ('old','new'):
  for work in ('answer','numeric','fib'):
   for repeat in range(3):
    cmd=engine(s,base,'reuse',work)
    _,so,se=j.run([clock,'1',str(len(cmd)),*cmd],'primary-reused-calls',deadline=30)
    lines=so.decode().splitlines();assert len(lines)==4 and lines[1]=='0'
    stderr=bytes.fromhex(lines[3]).decode();parts=stderr.split();assert len(parts)==6 and parts[0]=='PHASES' and parts[-1]=='20'
    assert bytes.fromhex(lines[2])==expected[work]*20
    values=list(map(int,parts[1:]));assert all(v>0 for v in values) and values[0]<=values[1]<=values[2]
    reused.append(dict(base=base,work=work,repeat=repeat,process_ns=int(lines[0]),context_ns=values[0],runtime_cumulative_ns=values[1],compile_cumulative_ns=values[2],calls_ns=values[3],calls=values[4]))
 write(out,'reused-calls.json',reused)
 # Complete context phase observations and diagnostic-overhead gate, separately from primary table.
 diag=[];plain=[]
 for repeat in range(3):
  for enabled in (False,True):
   for stdio in (False,True):
    _,so,se=j.run(profile(s,enabled,stdio,repeats=20),'profile-phases',deadline=30);assert not so;rows=parsed(se);assert len(rows)==20;profile_valid(rows,enabled)
    diag.append(dict(repeat=repeat,enabled=enabled,stdio=stdio,rows=rows))
  for stdio in (False,True):
   _,so,se=j.run([s['new']['primary']['path'],'contexts','true' if stdio else 'false','20'],'unmodified-context-phases');assert not so
   lines=se.decode().splitlines();assert len(lines)==20
   for i,line in enumerate(lines):
    v=line.split();assert v[0]=='CTX' and int(v[1])==i
    plain.append(dict(repeat=repeat,stdio=stdio,iteration=i,context_ns=int(v[2]),drop_ns=int(v[3])))
 write(out,'profile.json',diag);write(out,'unmodified-context.json',plain)
 a=statistics.median(r['context_ns'] for r in plain if r['stdio']);b=statistics.median(row['construct_ns'] for d in diag if d['enabled'] and d['stdio'] for row in d['rows'])
 write(out,'profile-overhead.json',dict(unmodified_median_ns=a,enabled_median_ns=b,ratio=b/a,passed=b/a<=1.20))
 assert b/a<=1.20,'STOP diagnostic overhead >20%; timing ranking not used'
 alloc_diag=[]
 for repeat in range(3):
  for stdio in (False,True):
   _,so,se=j.run(profile(s,True,stdio,repeats=20,kind='allocation'),'complete-profile-allocation',deadline=30);assert not so
   rows=parsed(se);profile_valid(rows,True);assert all(v['allocation'] is not None for row in rows for v in row['rows'])
   alloc_diag.append(dict(repeat=repeat,stdio=stdio,rows=rows))
 write(out,'profile-allocation.json',alloc_diag)
 j.run([sys.executable,P/'counters.py',out],'counter-alloc-rss',deadline=180)
