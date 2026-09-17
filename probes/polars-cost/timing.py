"""Pinned warm launches: primary products, generated-direct and feature alignment."""
import hashlib,json,os,pathlib,random,shutil,statistics,subprocess,tempfile,time
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1];ROOT=BENCH.parent/'rnx';OUT=BENCH/'results/polars-cost-0058';WORK=HERE/'target';PROJECT=WORK/'project';PROJECT.mkdir(parents=True,exist_ok=True)
APP=ROOT/'adapters/polars/target/release/rnx-polars';PYTHON=WORK/'python/bin/python';TOOL=ROOT/'tools/project/target/release/rnx-project'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_','POLARS_'))};ENV.pop('PYTHONDONTWRITEBYTECODE',None);ENV.update(TERM='xterm',NO_COLOR='1',POLARS_MAX_THREADS='1',RNX_CONFIG=str(WORK/'absent'),RNX_HISTORY=str(WORK/'history'))
shutil.copy2(HERE/'main.rn',PROJECT/'main.rn')
(PROJECT/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath='+json.dumps(str(ROOT))+'\n[native.polars]\npath='+json.dumps(str(ROOT/'adapters/polars'))+'\npackage="rnx-polars"\nbuilder="build"\nhook="plain"\n')
def logged(name,cmd):
 with (OUT/(name+'.log')).open('w') as f:p=subprocess.run(list(map(str,cmd)),env=ENV,stdout=f,stderr=subprocess.STDOUT)
 assert p.returncode==0,name
# Compilation/setup are outside all measured launch samples.
target=PROJECT/'.rnx/target'
if not target.exists():
 target.mkdir(parents=True);subprocess.run(['cp','-a','--reflink=auto',str(ROOT/'adapters/polars/target/release'),str(target/'release')],check=True)
for op in ['lock','build']:logged('project-'+op,[TOOL,op,'--manifest',PROJECT/'rnx.toml','--offline'])
receipt=json.loads((PROJECT/'.rnx/receipt.json').read_text());GENERATED=PROJECT/'.rnx/artifacts'/receipt['executable_sha256']
logged('project-prime',[TOOL,'run','--manifest',PROJECT/'rnx.toml','--','init'])
MAP=next((PROJECT/'.rnx/maps').glob('*.json'));ENTRY=PROJECT/'main.rn'
aligned=WORK/'aligned'
if not aligned.exists():
 aligned.mkdir();subprocess.run(['cp','-a','--reflink=auto',str(ROOT/'adapters/polars/target/release'),str(aligned/'release')],check=True)
logged('aligned-build',['cargo','build','--release','--locked','--offline','--manifest-path',ROOT/'adapters/polars/Cargo.toml','--features','rnx/project-sources','--target-dir',aligned])
ALIGNED=aligned/'release/rnx-polars'
assembly=next((PROJECT/'.rnx').rglob('src/main.rs')).parent.parent
nodes={}
for name,manifest,features in [('ordinary',ROOT/'adapters/polars/Cargo.toml',[]),('aligned',ROOT/'adapters/polars/Cargo.toml',['--features','rnx/project-sources']),('generated',assembly/'Cargo.toml',[])]:
 m=json.loads(subprocess.check_output(['cargo','metadata','--locked','--offline','--format-version','1','--manifest-path',str(manifest),*features],env=ENV))
 packages={p['id']:p for p in m['packages']}
 nodes[name]={packages[n['id']]['name']+'@'+packages[n['id']]['version']:n['features'] for n in m['resolve']['nodes'] if packages[n['id']]['name'] not in ['rnx-polars','rnx-project-app']}
assert nodes['aligned']==nodes['generated']
diff={k:{n:nodes[n].get(k) for n in nodes} for k in set().union(*nodes.values()) if nodes['ordinary'].get(k)!=nodes['generated'].get(k)}
(OUT/'feature-comparison.json').write_text(json.dumps({'differences':diff,'aligned_equals_generated':True,'nodes':nodes},indent=2)+'\n')
lock=json.loads((PROJECT/'rnx.lock').read_text())
# Sum unique trees; paths shared by package associations are fingerprinted once.
def trees(value):
 if isinstance(value,dict):
  if 'root' in value and 'files' in value and 'sha256' in value:yield value
  for v in value.values():yield from trees(v)
 elif isinstance(value,list):
  for v in value:yield from trees(v)
unique={t['root']:t for t in trees(lock['inputs'])};input_bytes=sum(f['bytes'] for t in unique.values() for f in t['files'])
CPU=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{CPU})
commands={'python':[str(PYTHON),str(HERE/'main.py')],'ordinary':[str(APP),'run',str(ENTRY)],'project':[str(TOOL),'run','--manifest',str(PROJECT/'rnx.toml'),'--'],'generated-direct':[str(GENERATED),'run','--source-map',str(MAP),str(ENTRY)],'aligned-direct':[str(ALIGNED),'run','--source-map',str(MAP),str(ENTRY)]}
expected={'init':'ready\n','pipeline':'DataFrame: 2 rows × 2 columns\n"category": string | "total": i64\n"a" | 2\n"🦀" | 7\n\n'}
samples=[]
def launch(name,mode,measure=True):
 with tempfile.TemporaryDirectory(prefix='rnx-polars-timing-') as temp:
  command=commands[name]+[mode,temp]
  start=time.perf_counter_ns();p=subprocess.run(command,env=ENV,capture_output=True,text=True,timeout=30);elapsed=(time.perf_counter_ns()-start)/1e6
  assert p.returncode==0 and not p.stderr and p.stdout==expected[mode],(name,mode,p.returncode,p.stdout,p.stderr)
  return elapsed
for mode in expected:
 for name in commands:launch(name,mode)
(OUT/'journal.jsonl').write_text('')
for repeat in range(2):
 for sample in range(30):
  order=[(name,mode) for name in commands for mode in expected];random.Random(58000+repeat*100+sample).shuffle(order)
  for name,mode in order:
   observation={'repeat':repeat,'sample':sample,'product':name,'mode':mode,'ms':launch(name,mode)}
   samples.append(observation)
   with (OUT/'journal.jsonl').open('a') as journal:journal.write(json.dumps(observation)+'\n')
 (OUT/'samples.json').write_text(json.dumps(samples,indent=2)+'\n');print('repeat',repeat,'complete',flush=True)
# Separate peak-RSS runs include native threads; GNU time is not in timing samples.
rss=[]
for repeat in range(3):
 for name in commands:
  for mode in expected:
   with tempfile.TemporaryDirectory() as tmp:
    p=subprocess.run(['/usr/bin/time','-f','%M','-o',tmp+'/rss',*commands[name],mode,tmp],env=ENV,capture_output=True,text=True,timeout=30)
    assert p.returncode==0 and not p.stderr and p.stdout==expected[mode]
    rss.append({'repeat':repeat,'product':name,'mode':mode,'peak_rss_kib':int(pathlib.Path(tmp,'rss').read_text())})
summary={}
for mode in expected:
 summary[mode]={name:[statistics.median(s['ms'] for s in samples if s['product']==name and s['mode']==mode and s['repeat']==r) for r in range(2)] for name in commands}
conditions={'cpu':CPU,'polars_threads':1,'samples_per_repeat_per_product_mode':30,'repeats':2,'seed':58000,'clock':'perf_counter_ns around no-shell spawn/capture/wait; harness overhead included equally','cache':'warm filesystem/process launches; normal Python pyc caching enabled, both modes warmed; no cold-cache claim','input_bytes':input_bytes,'input_trees':{k:sum(f['bytes'] for f in t['files']) for k,t in unique.items()},'commands':commands,'binaries':{name:{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for name,p in [('ordinary',APP),('generated',GENERATED),('aligned',ALIGNED),('project-tool',TOOL),('python',PYTHON.resolve())]},'rustc':subprocess.check_output(['rustc','-Vv'],text=True),'cpu_info':subprocess.check_output(['lscpu'],text=True),'RUSTFLAGS':'unset; standard release portable target, no target-cpu override','allocators':'rnx counting System allocator; Python/runtime wheel own allocators; no equality claim','provenance':'gate 1 different revisions; boundary-only attribution unproved','codec':'uncompressed; row groups 512^2 default on Rust and explicitly same on Python; no fsync'}
for name,obj in [('conditions',conditions),('summary',summary),('rss',rss)]: (OUT/(name+'.json')).write_text(json.dumps(obj,indent=2)+'\n')
for name in ['rnx.lock','rnx.Cargo.lock'] :shutil.copy2(PROJECT/name,OUT/name)
print(json.dumps(summary,indent=2),flush=True)
