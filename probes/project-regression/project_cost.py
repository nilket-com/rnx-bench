#!/usr/bin/env python3
"""Real generated PostgreSQL/plain assembly: empty target, warm build, verified run."""
import hashlib,json,os,pathlib,shutil,statistics,subprocess,time
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1];ROOT=BENCH.parent/'rnx';OUT=BENCH/'results/project-regression-0057'
TOOL=ROOT/'tools/project/target/release/rnx-project';WORK=HERE/'target/cost';WORK.mkdir(parents=True,exist_ok=True)
PLAIN=BENCH/'probes/package-assembly/target/plain';WORDS=BENCH/'probes/package-assembly/target/words'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_'))};ENV.update(TERM='xterm',NO_COLOR='1',RNX_CONFIG=str(WORK/'absent'))
manifest=WORK/'rnx.toml';manifest.write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath='+json.dumps(str(ROOT))+'\n[sources.words]\npath='+json.dumps(str(WORDS))+'\n[native.local]\npath='+json.dumps(str(PLAIN))+'\npackage="gate-four-plain"\nbuilder="build"\nhook="plain"\n[native.postgres]\npath='+json.dumps(str(ROOT/'adapters/postgres'))+'\npackage="rnx-postgres"\nbuilder="build"\nhook="lifecycle"\n')
(WORK/'main.rn').write_text('mod words; pub fn main(_) { local::answer()+words::one() }\n')
if (WORK/'.rnx').exists():shutil.rmtree(WORK/'.rnx')
report={'conditions':{'first_build':'empty .rnx target; registry sources already cached; offline; no copied artifacts','warm_build':'same target immediately after first build','run_clock':'perf_counter_ns around subprocess; includes spawn/wait equally; ABBA 20 pairs, CPU 4','assembly':'real rnx, postgres and plain extensions, mapped words; no database connection in timed input'},'seconds':{}}
def product(op,tag):
    start=time.perf_counter();p=subprocess.run([str(TOOL),op,'--manifest',str(manifest),'--offline'],env=ENV,capture_output=True,timeout=1200)
    report['seconds'][tag]=time.perf_counter()-start;(OUT/f'cost-{tag}.log').write_bytes(p.stdout+p.stderr)
    assert p.returncode==0,(tag,p.stderr[-4000:]);print(tag,report['seconds'][tag],flush=True)
product('lock','lock');product('build','first-build');product('build','warm-build')
receipt=json.loads((WORK/'.rnx/receipt.json').read_text());exe=WORK/'.rnx/artifacts'/receipt['executable_sha256'];mapfile=next((WORK/'.rnx/maps').glob('*.json'),None)
# Run once to publish the map; then compare exactly the same executable/source.
p=subprocess.run([str(TOOL),'run','--manifest',str(manifest)],env=ENV,capture_output=True,check=True);assert p.stdout==b'3\n',p.stdout
mapfile=next((WORK/'.rnx/maps').glob('*.json'))
commands={'direct':[str(exe),'run','--source-map',str(mapfile),str(WORK/'main.rn')],'project':[str(TOOL),'run','--manifest',str(manifest)]}
os.sched_setaffinity(0,{4});samples={k:[] for k in commands}
for i in range(23):
    for name in (['direct','project'] if i%2==0 else ['project','direct']):
        start=time.perf_counter_ns();p=subprocess.run(commands[name],env=ENV,capture_output=True,timeout=60);elapsed=(time.perf_counter_ns()-start)/1e6
        assert p.returncode==0 and p.stdout==b'3\n',(name,p.stdout,p.stderr)
        if i>=3:samples[name].append(elapsed)
report['run_samples_ms']=samples;report['run_median_ms']={k:statistics.median(v) for k,v in samples.items()};report['verification_overhead_ms']=report['run_median_ms']['project']-report['run_median_ms']['direct'];report['receipt']=receipt
report['lock_sha256']=hashlib.sha256((WORK/'rnx.lock').read_bytes()).hexdigest();report['tool_sha256']=hashlib.sha256(TOOL.read_bytes()).hexdigest()
(OUT/'project-cost.json').write_text(json.dumps(report,indent=2)+'\n');print(report['run_median_ms'],flush=True)
