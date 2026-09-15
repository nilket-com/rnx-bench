# Historical comparison for the 0044 revisions, which register host::.
# Use probes/namespaces/measure.py for the 0049 migration and current binaries.
#!/usr/bin/env python3
"""0044: matched one-shot and supervised-child process costs (Linux fixture)."""
import hashlib,json,os,pathlib,shlex,subprocess,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[2]
before,after=map(lambda p:str(pathlib.Path(p).resolve()),sys.argv[1:3])
os.chdir(root)
out=root/'results/process_0044';out.mkdir(parents=True,exist_ok=True)
conditions={'binaries':{},'outputs':{},'memory':{},'versions':{}}
with tempfile.TemporaryDirectory() as tmp:
    os.environ.update(TERM='xterm',RNX_CONFIG=tmp+'/absent',RNX_HISTORY=tmp+'/history')
    for k in ['RNX_MEMORY_CEILING','NO_COLOR']:os.environ.pop(k,None)
    for k in list(os.environ):
        if k.startswith('RNX_TEST_'):os.environ.pop(k)
    commands=[]
    for label,binary in [('before',before),('after',after)]:
        data=pathlib.Path(binary).read_bytes()
        conditions['binaries'][label]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        cases=[('version',['version']),('eval',['eval','42']),('run',['run','scripts/bare.rn']),('json',['run','probes/process/json-0044.rn']),('child',['eval','host::process("/bin/true", [], 30000)?.code'])]
        if label=='after':cases.append(('facade',['eval','process::run("/bin/true", [], #{})?.code']))
        for name,args in cases:
            cmd=[binary,*args];ran=subprocess.run(cmd,capture_output=True);assert ran.returncode==0,ran.stderr
            conditions['outputs'][name+' '+label]={'stdout':ran.stdout.decode(),'stderr':ran.stderr.decode(),'exit':ran.returncode}
            commands.append((name+' '+label,cmd))
        ran=subprocess.run([binary,'--no-splash'],input=b':memory\n:q\n',capture_output=True)
        assert ran.returncode==0
        conditions['memory'][label]={'stdout':ran.stdout.decode(),'stderr':ran.stderr.decode()}
    for name in ['version','eval','run','json','child']:
        assert conditions['outputs'][name+' before']==conditions['outputs'][name+' after']
    assert conditions['outputs']['child after']==conditions['outputs']['facade after']
    for cmd in [['rustc','--version'],['hyperfine','--version'],['uname','-a']]:
        conditions['versions'][' '.join(cmd)]=subprocess.check_output(cmd,text=True).strip()
    conditions['core']=4;conditions['commands']=commands
    (out/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
    cmd=['taskset','-c','4','hyperfine','-N','--warmup','10','--runs','100','--export-json',str(out/'timings.json')]
    for name,args in commands:cmd+=['--command-name',name,shlex.join(args)]
    subprocess.run(cmd,check=True)
r=json.loads((out/'timings.json').read_text())['results']
(out/'README.md').write_text('# Record 0044 timings\n\nWhole-process elapsed times, startup included. Core 4, 10 warmups, 100 runs.\nOutput equality and binary hashes are in conditions.json.\n\n| command | mean ms | sigma ms |\n| --- | ---: | ---: |\n'+''.join(f"| {x['command']} | {x['mean']*1000:.3f} | {x['stddev']*1000:.3f} |\n" for x in r))
