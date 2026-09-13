#!/usr/bin/env python3
"""Record 0036: before/after release binaries, no network; run from rnx-bench."""
import hashlib,json,os,pathlib,shlex,subprocess,sys,tempfile
before,after=map(lambda p:str(pathlib.Path(p).resolve()),sys.argv[1:3])
env={'PATH':os.environ.get('PATH',''), 'TERM':'dumb'}
results=pathlib.Path('results'); results.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='rnx-env-bench-') as tmp:
    entries=[]
    for name,args in [('version',['version']),('help',['help']),('eval',['eval','42']),('run',['run','scripts/bare.rn']),('json',['run','scripts/json.rn'])]:
        entries.extend((name+' '+label,[exe,*args]) for label,exe in [('before',before),('after',after)])
    script=pathlib.Path(tmp)/'args.rn';script.write_text('pub fn main(args) { args.len() }\n')
    for label,exe in [('before',before),('after',after)]:
        entries.append(('arguments '+label,[exe,'run',str(script),*(['two words', '--flag', '', 'é']*25)]))
    outputs=[]
    for name,cmd in entries:
        run=subprocess.run(cmd,env=env,capture_output=True,check=True)
        outputs.append({'name':name,'stdout':run.stdout.decode(),'stderr':run.stderr.decode(),'exit':run.returncode})
    for i in range(0,len(outputs),2):
        # Help intentionally has a new public surface.
        if not outputs[i]['name'].startswith('help'):
            assert outputs[i]['stdout']==outputs[i+1]['stdout'] and outputs[i]['stderr']==outputs[i+1]['stderr']
    cmd=['taskset','-c','4','hyperfine','-N','--warmup','10','--runs','50','--export-json',str(results/'env_0036_startup.json')]
    for name,args in entries: cmd+=['--command-name',name,shlex.join(args)]
    subprocess.run(cmd,env=env,check=True)
    info={'commands':entries,'outputs':outputs,'versions':{},'binaries':{},'memory':{}}
    for command in [['rustc','--version'],['hyperfine','--version'],['uname','-a']]:
        info['versions'][' '.join(command)]=subprocess.check_output(command,text=True).strip()
    for name,exe in [('before',before),('after',after)]:
        b=pathlib.Path(exe).read_bytes();info['binaries'][name]={'path':exe,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
        run=subprocess.run([exe],input=':memory\n:quit\n',text=True,capture_output=True,env=env,check=True)
        info['memory'][name]={'stdout':run.stdout,'stderr':run.stderr}
    (results/'env_0036_conditions.json').write_text(json.dumps(info,indent=2)+'\n')
