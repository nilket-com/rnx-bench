"""Pinned, interleaved full-product and fixed-target observations; all samples retained."""
from pathlib import Path
import os,subprocess as sp,json,time,random,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/native-inventory-0065'
rows=json.loads((O/'setup.json').read_text());assert all('artifact' in r for r in rows if r['layout']=='shallow')
E=json.loads((W/'env.json').read_text());cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
N=int(os.environ.get('RNX_INVENTORY_SAMPLES','30'));journal=O/'samples.jsonl';assert not journal.exists(),'preserve prior journal before rerun'
cells=[]
for row in rows:
 for route in ['stock','clocks-off','profile']:
  tool=W/('stock' if route=='stock' else 'timed')/'tools/project/target/release/inventory-probe'
  cells.append(dict(kind='fixed',layout=row['layout'],count=row['count'],route=route,args=[str(tool),row['config']]))
for row in rows:
 if row['layout']!='shallow':continue
 for route in ['stock','profile','direct']:
  if route=='direct':args=[row['artifact'],'--no-splash','--color=never','eval','42']
  else:args=[str(W/('stock' if route=='stock' else 'timed')/'tools/project/target/release/rnx-project'),'eval','--manifest',row['manifest'],'--','42']
  cells.append(dict(kind='product',layout='shallow',count=row['count'],route=route,args=args))
cells.append(dict(kind='fixed-direct',layout='all',count=-1,route='direct',args=[str(W/'fixed-rnx'),'--no-splash','--color=never','eval','42']))
def sample(cell):
 env=dict(E)
 if cell['route']=='profile':env['RNX_INVENTORY_CLOCKS']='1'
 t=time.perf_counter_ns();p=sp.run(cell['args'],cwd=W,env=env,capture_output=True,text=True,timeout=15);ns=time.perf_counter_ns()-t
 assert p.returncode==0 and p.stdout=='42\n',(cell,p.returncode,p.stdout,p.stderr)
 result=dict(cell,wall_ns=ns)
 lines=p.stderr.splitlines();profiles=[s for s in lines if s.startswith('INVENTORY_PROFILE ')];details=[s for s in lines if s.startswith('INVENTORY_RESULT ')]
 assert len(lines)==len(profiles)+len(details),(cell,p.stderr)
 if cell['route']=='profile':assert len(profiles)==1;result['profile']=json.loads(profiles[0].split(' ',1)[1])
 else:assert not profiles
 if cell['kind']=='fixed':
  assert len(details)==1
  _,digest,ms=details[0].split();result.update(inventory_digest=digest,inventory_ms=float(ms))
 else:assert not details
 return result
# Explicit warmups outside the measured journal; no rejected measured samples.
for cell in cells:
 for _ in range(2):sample(cell)
with journal.open('w') as f:
 for repeat in range(2):
  work=[(cell,i) for cell in cells for i in range(N)];random.Random(650001+repeat).shuffle(work)
  for cell,i in work:
   result=sample(cell);result.update(repeat=repeat,sample=i);f.write(json.dumps(result,separators=(',',':'))+'\n');f.flush()
  print('PASS repeat',repeat,len(work),'samples',flush=True)
hashes={}
for name in ['stock','timed']:
 for binary in ['rnx-project','inventory-probe']:
  p=W/name/'tools/project/target/release'/binary;hashes[name+'/'+binary]=hashlib.sha256(p.read_bytes()).hexdigest()
(O/'measurement.json').write_text(json.dumps(dict(cpu=cpu,samples_per_cell=N,repeats=2,cells=len(cells),total=2*N*len(cells),warmups=2,seed_base=650001,polars_threads=1,binary_hashes=hashes,scope='warm single-host Linux; full product uses its own direct artifact, fixed-target probe always execs identical stock rnx; no samples discarded'),indent=2)+'\n')
