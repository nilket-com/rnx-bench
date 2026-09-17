#!/usr/bin/env python3
"""Hyperfine no-shell measurements, AB then BA; run with an otherwise idle host."""
import json,os,pathlib,shlex,subprocess
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1];OUT=BENCH/'results/project-regression-0057'
build=json.loads((OUT/'build.json').read_text());bins={k:v['path'] for k,v in build['binaries'].items()}
work=HERE/'target/startup';work.mkdir(parents=True,exist_ok=True)
source=work/'main.rn';source.write_text('pub fn main(_) {42}\n')
env={k:v for k,v in os.environ.items() if not k.startswith('RNX_')};env.update(TERM='xterm',NO_COLOR='1',RNX_CONFIG=str(work/'absent'))
os.sched_setaffinity(0,{4})
workloads={'version':['version'],'help':['help'],'run':['run',str(source)],'eval':['eval','42'],'json':['run',str(BENCH/'scripts/json.rn')]}
for repeat,order in enumerate([['before','after'],['after','before']],1):
    for name,args in workloads.items():
        command=['hyperfine','-N','--warmup','10','--runs','100','--export-json',str(OUT/f'startup-{repeat}-{name}.json')]
        for which in order:command += ['-n',which,shlex.join([bins[which],*args])]
        with (OUT/f'startup-{repeat}-{name}.log').open('w') as out:subprocess.run(command,env=env,stdout=out,stderr=subprocess.STDOUT,check=True)
        print(repeat,name,flush=True)
