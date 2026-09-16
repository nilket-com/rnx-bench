#!/usr/bin/env python3
"""Matched process timings, ABBA rounds on one CPU. No shell per sample."""
import hashlib,json,os,pathlib,statistics,subprocess,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/http-lifecycle-0055';OUT.mkdir(exist_ok=True,parents=True)
bins={'before':pathlib.Path(os.environ.get('RNX_HTTP_BEFORE','/tmp/rnx-0055-baseline/rnx')),'after':ROOT.parent/'rnx/target/release/rnx'}
env={k:v for k,v in os.environ.items() if not k.startswith('RNX_')};env.update(TERM='xterm',NO_COLOR='1',RNX_CONFIG='/nonexistent-rnx-0055-config')
os.sched_setaffinity(0,{4})
sources={'cpu':'pub fn main(_) { let n=0; let sum=0; while n<100000 { sum+=n; n+=1; }; sum }', 'strings':'pub fn main(_) { let n=0; let s=""; while n<10000 { s.push_str("abc"); n+=1; }; s.len() }'}
result={'binaries':{k:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for k,p in bins.items()},'source':sources,'conditions':{'cpu':4,'warmups':8,'rounds':'ABBA twice, 20 per block','timing':'subprocess wall time, includes spawn/wait; no per-sample shell','rustc':subprocess.check_output(['rustc','-Vv'],text=True)},'cases':{}}
with tempfile.TemporaryDirectory(prefix='rnx-0055-cost-') as tmp:
    for k,v in sources.items():pathlib.Path(tmp,k+'.rn').write_text(v)
    cases={'version':['version'],'help':['help'],'bare-run':['run',str(ROOT/'scripts/bare.rn')],'bare-eval':['eval','42'],'JSON-10k':['run',str(ROOT/'scripts/json.rn')],'cpu':['run',tmp+'/cpu.rn'],'strings':['run',tmp+'/strings.rn']}
    for name,args in cases.items():
        samples={k:[] for k in bins}; outputs={}
        def once(k):
            t=time.perf_counter_ns();p=subprocess.run([str(bins[k]),*args],env=env,capture_output=True,timeout=10);elapsed=(time.perf_counter_ns()-t)/1e6
            assert p.returncode==0,(name,p.stderr);outputs[k]=(p.stdout,p.stderr);return elapsed
        for k in bins:
            for _ in range(8):once(k)
        for k in ['before','after','after','before']*2:
            for _ in range(20):samples[k].append(once(k))
        assert outputs['before']==outputs['after'],name
        entry={'samples_ms':samples,'median_ms':{k:statistics.median(v) for k,v in samples.items()},'stdout':outputs['after'][0].decode()}
        entry['change_percent']=(entry['median_ms']['after']/entry['median_ms']['before']-1)*100
        result['cases'][name]=entry
        print(name,entry['median_ms'],round(entry['change_percent'],2),flush=True)
        (OUT/'timing.json').write_text(json.dumps(result,indent=2)+'\n')
