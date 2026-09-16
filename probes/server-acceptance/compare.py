#!/usr/bin/env python3
"""Exact CLI bytes, then seven workloads in ABBA twice on one inherited CPU."""
import argparse,hashlib,json,os,pathlib,statistics,subprocess,tempfile,time
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1];OUT=BENCH/'results/server-acceptance-0056'
build=json.loads((OUT/'build.json').read_text());bins={k:v['path'] for k,v in build['binaries'].items()}
ap=argparse.ArgumentParser();ap.add_argument('--repeat',default='1');args=ap.parse_args()
env={k:v for k,v in os.environ.items() if not k.startswith('RNX_')};env.update(TERM='xterm',NO_COLOR='1')
cpu=4 if 4 in os.sched_getaffinity(0) else min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
sources={
 'bare':'pub fn main(_) { 42 }',
 'args':'pub fn main(args) { args }',
 'compile':'pub fn main(_) {\n let x = ;\n}',
 'runtime':'fn inner() {\n [1][7]\n}\npub fn main(_) { inner() }',
 'method':'pub fn main(_) { 1.missing() }',
 'returned-error':'pub fn main(_) { Err("bad") }',
 'struct':'struct P { x }\npub fn main(_) { P { x: 42 } }',
 'unit':'pub fn main(_) {}',
 'streams':'pub fn main(_) { print!("out"); io::eprint("err")?; 42 }',
 'budget':'pub fn main(_) { loop {} }',
 'cpu':'pub fn main(_) { let n=0; let sum=0; while n<100000 { sum+=n; n+=1; }; sum }',
 'strings':'pub fn main(_) { let n=0; let s=""; while n<10000 { s.push_str("abc"); n+=1; }; s.len() }',
}
with tempfile.TemporaryDirectory(prefix='rnx 0056 compare ') as tmp:
    d=pathlib.Path(tmp);env.update(RNX_CONFIG=str(d/'absent'),RNX_HISTORY=str(d/'history'))
    for name,source in sources.items():(d/(name+'.rn')).write_text(source)
    cases={name:(['run',*(['--budget','100'] if name=='budget' else []),str(d/(name+'.rn')),*(['abc','--budget','3'] if name=='args' else [])],b'') for name in sources}
    for name,command in [('version',['version']),('help',['help']),('eval',['eval','42']),('eval-missing',['eval']),('run-missing',['run']),('file-missing',['run',str(d/'missing.rn')]),('budget-text',['run','--budget','bad']),('budget-zero',['run','--budget','0']),('budget-max',['run','--budget',str(2**64-1)]),('debug',['run','--debug-source',str(d/'bare.rn')]),('debug-error',['run','--debug-source',str(d/'compile.rn')]),('json',['run',str(BENCH/'scripts/json.rn')])]:cases[name]=(command,b'')
    cases['session']=([],b'let x=42\nx\n:renumber\nx+1\n:reset\n:q\n')
    compared={}
    def run(which,command,input=b''):
        return subprocess.run([bins[which],*command],env=env,input=input,capture_output=True,timeout=20)
    for name,(command,input) in cases.items():
        observed={}
        for which in bins:
            r=run(which,command,input);observed[which]={'exit':r.returncode,'stdout_hex':r.stdout.hex(),'stderr_hex':r.stderr.hex()}
        assert observed['before']==observed['after'],(name,observed)
        compared[name]=observed['after']
    (OUT/'comparison.json').write_text(json.dumps({'build':build,'sources':sources,'cases':compared,'equal_cases':len(compared)},indent=2)+'\n')
    workloads={'version':['version'],'help':['help'],'bare-run':['run',str(d/'bare.rn')],'bare-eval':['eval','42'],'JSON-10k':['run',str(BENCH/'scripts/json.rn')],'cpu':['run',str(d/'cpu.rn')],'strings':['run',str(d/'strings.rn')]}
    report={'conditions':{'cpu':cpu,'warmups':8,'order':['before','after','after','before']*2,'samples_per_block':20,'clock':'perf_counter_ns around spawn/communicate; no shell; inherited affinity'},'binaries':build['binaries'],'sources':sources,'cases':{}}
    for name,command in workloads.items():
        samples={k:[] for k in bins}
        def once(which):
            at=time.perf_counter_ns();r=run(which,command);elapsed=(time.perf_counter_ns()-at)/1e6
            assert r.returncode==0,(name,r.stderr);return elapsed
        for which in bins:
            for _ in range(8):once(which)
        blocks=[]
        for which in report['conditions']['order']:
            values=[once(which) for _ in range(20)];samples[which].extend(values);blocks.append({'binary':which,'median_ms':statistics.median(values)})
        medians={k:statistics.median(v) for k,v in samples.items()}
        report['cases'][name]={'samples_ms':samples,'blocks':blocks,'median_ms':medians,'change_percent':100*(medians['after']/medians['before']-1)}
        (OUT/f'timing-{args.repeat}.json').write_text(json.dumps(report,indent=2)+'\n')
        print(name,medians,report['cases'][name]['change_percent'],flush=True)
