"""Pre-registered round-2 no-keep-alive slot diagnostic, using the unchanged host/load code.
SWAP: new in slot A, old in slot B. AA: old in both. No product changes.
"""
import importlib.util,json,pathlib,statistics,subprocess,sys
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('web0166',HERE/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
PIN='8ec20aca0de0a294bfdb0024a89c7e69296d1bf9004237c0176e0599ce818fd8'
CONDITION=('/hello/world',1,False)
RULE={'a':'SWAP old_B/new_A <= .95 and AA B/A < 1: slot effect; run corrected ABBA gate', 'b':'SWAP new_A/old_B <= .95 and abs(AA B/A-1) <= .02: source effect; profile', 'c':'otherwise stop and report'}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def summary(loads):
 return [{'slot':n,'rps':statistics.median(r['rps'] for r in loads if r['impl']==n),'rps_range':[min(r['rps'] for r in loads if r['impl']==n),max(r['rps'] for r in loads if r['impl']==n)]} for n in 'AB']
def validate(out):
 meta=json.loads((out/'conditions.json').read_text());kind=meta['kind'];mapping={'swap':{'A':'after.rn','B':'before.rn'},'aa':{'A':'before.rn','B':'before.rn'}}[kind]
 assert meta['binary_sha256']==PIN and meta['mapping']==mapping and meta['decision_rule']==RULE
 assert meta['server_cpus']==m.b.SERVER_CPUS and meta['load_cpus']==m.b.LOAD_CPUS
 for slot,source in mapping.items():assert m.sha(out/'sources'/('before.rn' if slot=='A' else 'after.rn'))==m.sha(HERE/source)
 rows=[json.loads(l) for l in (out/'results.jsonl').read_text().splitlines()];loads=[r for r in rows if r['case']=='load']
 ready=[r for r in rows if r['case']=='ready'];assert [r['impl'] for r in ready]==list('AB')
 for r in ready:
  n=r['impl'];assert r['argv']==[str(m.STOCK),'serve','--bind',f'127.0.0.1:{m.b.PORTS[n]}','--workers','2','--log','off',str(out/'sources'/('before.rn' if n=='A' else 'after.rn'))]
 expected=[(n,rep,*CONDITION) for rep in range(3) for n in ('AB' if rep%2==0 else 'BA')]
 assert [(r['impl'],r['rep'],r['route'],r['concurrency'],r['keepalive']) for r in loads]==expected
 files=sorted(out.glob('oha-*.json'));assert [f.name for f in files]==[f'oha-{i:03}.json' for i in range(12)]
 for j,r in enumerate(loads):
  for phase in [0,1]:
   a=json.loads(files[2*j+phase].read_text());seconds=3 if phase==0 else 10
   assert a['exit']==0 and json.loads(a['stdout'])==a['result']
   assert (a['port'],a['route'],a['concurrency'],a['seconds'],a['keepalive'])==(m.b.PORTS[r['impl']],*CONDITION[:2],seconds,False)
   argv=['taskset','-c',m.b.LOAD_CPUS,'oha','--no-tui','--output-format','json','-z',f'{seconds}s','-c','1','-w','--http-version','1.1','--disable-keepalive',f'http://127.0.0.1:{a["port"]}/hello/world']
   assert a['argv']==argv
   v=m.b.validate(a['result'],1,False,r.get('connections') if phase else None)
  assert all(r[k]==v[k] for k in v)
 assert json.loads((out/'summary.json').read_text())==summary(loads)
 print(kind+': 6 measured rows + 12 full artifacts, identities/commands/exits/fields/summary PASS',flush=True)
 return summary(loads)
def run(kind,out):
 assert m.sha(m.STOCK)==PIN
 out.mkdir(parents=True,exist_ok=False);sources=out/'sources';sources.mkdir()
 mapping={'swap':{'A':'after.rn','B':'before.rn'},'aa':{'A':'before.rn','B':'before.rn'}}[kind]
 for slot,source in mapping.items():(sources/('before.rn' if slot=='A' else 'after.rn')).write_bytes((HERE/source).read_bytes())
 save(out/'conditions.json',{'kind':kind,'mapping':mapping,'binary_sha256':PIN,'server_cpus':m.b.SERVER_CPUS,'load_cpus':m.b.LOAD_CPUS,'decision_rule':RULE})
 m.HERE=sources;rows=[];procs={};logs={};serial=0
 def oha(port,route,c,seconds,ka):
  nonlocal serial
  cmd=['taskset','-c',m.b.LOAD_CPUS,'oha','--no-tui','--output-format','json','-z',f'{seconds}s','-c',str(c),'-w','--http-version','1.1','--disable-keepalive',f'http://127.0.0.1:{port}{route}']
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=seconds+20)
  a={'port':port,'route':route,'concurrency':c,'seconds':seconds,'keepalive':ka,'argv':cmd,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
  try:a['result']=json.loads(p.stdout)
  except json.JSONDecodeError:a['result']=None
  save(out/f'oha-{serial:03}.json',a);serial+=1
  assert p.returncode==0 and a['result'] is not None
  return a['result']
 m.b.oha=oha
 try:
  for n in 'AB':
   p,ms,cmd=m.start(n,out,logs);procs[n]=p;rows.append({'case':'ready','impl':n,'ready_ms':ms,'argv':cmd})
  for rep in range(3):
   for n in ('AB' if rep%2==0 else 'BA'):
    r=m.b.measure(n,procs[n],*CONDITION,rep==0);row={'case':'load','rep':rep,'impl':n,'route':CONDITION[0],'concurrency':1,'keepalive':False,**r};rows.append(row);print(json.dumps(row),flush=True)
 finally:
  for p in procs.values():
   if p.poll() is None:p.terminate()
   p.wait(timeout=15)
  for log in logs.values():log.close()
  (out/'results.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
 save(out/'summary.json',summary([r for r in rows if r['case']=='load']));return validate(out)
def decision(root):
 swap=validate(root/'swap');aa=validate(root/'aa');sr=swap[1]['rps']/swap[0]['rps'];ar=aa[1]['rps']/aa[0]['rps']
 result='a' if sr<=.95 and ar<1 else ('b' if 1/sr<=.95 and abs(ar-1)<=.02 else 'c')
 d={'swap_old_B_over_new_A':sr,'aa_B_over_A':ar,'decision':result,'rule':RULE};save(root/'decision.json',d);print(json.dumps(d,indent=2),flush=True)
if __name__=='__main__':
 if sys.argv[1]=='--validate':validate(pathlib.Path(sys.argv[2]))
 elif sys.argv[1]=='--decision':decision(pathlib.Path(sys.argv[2]))
 else:
  root=pathlib.Path(sys.argv[1]).resolve();root.mkdir(parents=True,exist_ok=False)
  run('swap',root/'swap');run('aa',root/'aa');decision(root)
