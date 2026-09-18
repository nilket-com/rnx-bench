"""Real Polars shared hit, override, and public interactive pipeline."""
from pathlib import Path
import json,os,subprocess as sp,time,random,shutil,sys,shlex,statistics as st
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/inventory-workflow-0065'
sys.path.insert(0,str(B/'probes/project-interactive'));from common import Terminal
rows=json.loads((O/'setup.json').read_text());tools=json.loads((O/'tools.json').read_text());E=json.loads((W/'env.json').read_text());E.update(RNX_CONFIG=str(W/'absent'),RNX_HISTORY=str(W/'real-history'),POLARS_MAX_THREADS='1')
cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
def call(a,extra=None,stdin=None):
 p=sp.run(list(map(str,a)),env=dict(E,**(extra or {})),cwd=W,input=stdin,capture_output=True,text=True,timeout=60);assert p.returncode==0,(a,p.stdout,p.stderr);return p
traps=W/'real-traps';traps.mkdir();marker=W/'compiler-trap'
for name,allowed in [('cargo','-V'),('rustc','-Vv')]:
 real=shutil.which(name);p=traps/name;p.write_text('#!/bin/sh\nif [ "$1" = '+shlex.quote(allowed)+' ]; then exec '+shlex.quote(real)+' "$@"; fi\nprintf invoked >> '+shlex.quote(str(marker))+'\nexit 91\n');p.chmod(0o755)
trapped={'PATH':str(traps)+':'+E['PATH']};apps={};results={}
for version in tools:
 d=W/('second-'+version);d.mkdir();m=d/'rnx.toml';m.write_bytes(Path(rows[1][version]['manifest']).read_bytes());(d/'entry.rn').write_text('pub fn main(_) { 43 }\n');tool=tools[version]['path'];call([tool,'lock','--offline','--manifest',m]);apps[version]=m
 # First attachment is checked independently before the timing warmup.
 p=call([tool,'build','--offline','--manifest',m],trapped);assert 'attached shared' in p.stderr and not marker.exists()
 assert call([tool,'run','--manifest',m]).stdout=='43\n'
 r=json.loads((d/'.rnx/receipt.json').read_text());first=json.loads((Path(rows[1][version]['manifest']).parent/'.rnx/receipt.json').read_text());assert r['assembly_key']==first['assembly_key']
 results[version]=dict(second_consumer_key=r['assembly_key'],different_application=True,no_compilation=True)
p=sp.run(['cargo','build'],env=dict(E,**trapped),capture_output=True);assert p.returncode==91 and marker.exists();marker.unlink()
journal=O/'attachment-samples.jsonl';assert not journal.exists()
attach=[]
with journal.open('w') as f:
 for repeat in range(2):
  jobs=[(version,i) for version in tools for i in range(30)];random.Random(652100+repeat).shuffle(jobs)
  for version,i in jobs:
   start=time.perf_counter_ns();p=call([tools[version]['path'],'build','--offline','--manifest',apps[version]],trapped);ms=(time.perf_counter_ns()-start)/1e6
   assert 'attached shared' in p.stderr and not marker.exists()
   r=dict(version=version,repeat=repeat,sample=i,ms=ms);attach.append(r);f.write(json.dumps(r)+'\n');f.flush()
(O/'attachment-summary.json').write_text(json.dumps(dict(cpu=cpu,full_artifact_hash=True,compiler_trap_positive_control=True,medians={v:[st.median(r['ms'] for r in attach if r['version']==v and r['repeat']==rep) for rep in range(2)] for v in tools}),indent=2)+'\n')
T=tools['current']['path'];a=W/'real-override';a.mkdir();m=a/'rnx.toml';(a/'entry.rn').write_text('pub fn main(_) { 42 }\n');m.write_text('format=1\n[application]\nentry="entry.rn"\n[executable]\npath='+json.dumps(rows[1]['current']['artifact'])+'\n')
call([T,'lock','--offline','--manifest',m]);call([T,'build','--manifest',m],trapped)
for kind,manifest in [('shared',apps['current']),('override',m)]:
 assert call([T,'eval','--manifest',manifest,'--','polars::lit(1).is_ok()']).stdout=='true\n'
 assert call([T,'run','--manifest',manifest]).stdout==('43\n' if kind=='shared' else '42\n')
 cwd=W/('journey-'+kind);cwd.mkdir();t=Terminal([T,'session','--manifest',manifest,'--no-splash','--color=never'],cwd,E)
 try:
  assert t.read()=='\r[1] > \r'
  t.send('fs::write_new("tiny.csv", "category,value\\na,1\\na,2\\n🦀,3\\n🦀,4\\nmissing,\\n").unwrap();')
  t.send('let frame = polars::read_csv("tiny.csv", [("category","string"),("value","i64")]).unwrap();')
  t.send('let grouped = frame.lazy().filter(polars::col("value").gt(polars::lit(1).unwrap())).group_by([polars::col("category")]).unwrap();')
  t.send('let plan = grouped.agg([polars::col("value").sum().alias("total")]).unwrap().sort(["category"]).unwrap();')
  t.send('let result = plan.collect().unwrap();');out=t.send('println!("{}", result.preview().unwrap());');assert '"a" | 2' in out and '"🦀" | 7' in out
  out=t.send('frame.lazy().sort(["missing"]).unwrap().collect()');assert 'Err' in out and 'missing' in out
  assert '5 rows' in t.send('println!("{}", frame.preview().unwrap());')
  t.send('result.write_parquet_new("tiny.parquet").unwrap();');assert 'error' not in t.send('assert!(polars::read_parquet("tiny.parquet").unwrap().preview().unwrap() == result.preview().unwrap());').lower()
  t.send(':reset');assert 'No local variable' in t.send('frame');assert 'true' in t.send('polars::lit(1).is_ok()')
  os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
 finally:
  (O/(kind+'-journey.log')).write_bytes(t.log);t.close()
 results[kind+'_journey']=True
(O/'real.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS real shared/override run, eval, session, second-consumer attachment and compiler trap')
