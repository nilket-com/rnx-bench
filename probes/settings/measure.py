#!/usr/bin/env python3
"""Record 0043: absent and six-colour config, same process conditions."""
import hashlib,json,os,pathlib,shlex,subprocess,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[2];os.chdir(root)
before,after=(str(pathlib.Path(p).resolve()) for p in sys.argv[1:3])
out=root/'results/settings_0043_session_only';out.mkdir(parents=True,exist_ok=True)
config=root/'probes/settings/config.rn'
commands=[];outputs=[];conditions={'commands':commands,'outputs':outputs,'binaries':{},'versions':{},'memory':{}}
for key in ['RNX_CONFIG','XDG_CONFIG_HOME','HOME','APPDATA','LOCALAPPDATA','NO_COLOR']:os.environ.pop(key,None)
os.environ['TERM']='xterm-256color'
with tempfile.TemporaryDirectory() as tmp:
    os.environ['RNX_HISTORY']=tmp+'/history'
    missing=tmp+'/missing.rn'
    for name,args in [('version',['version']),('help',['help']),('eval',['eval','42']),('run',['run','scripts/bare.rn']),('json',['run','scripts/json.rn']),('session',['--no-splash','repl'])]:
        pair=[]
        for label,binary,path in [('before',before,missing),('after',after,missing),('configured',after,str(config))]:
            cmd=['env','RNX_CONFIG='+path,binary,*args];commands.append((name+' '+label,cmd))
            ran=subprocess.run(cmd,input=b':q\n',capture_output=True);assert ran.returncode==0,ran.stderr
            pair.append((ran.stdout,ran.stderr));outputs.append(dict(name=name+' '+label,stdout=ran.stdout.decode(),stderr=ran.stderr.decode(),exit=ran.returncode))
        assert pair[0]==pair[1]==pair[2],(name,pair)
    for label,binary,path in [('before',before,missing),('after',after,missing),('configured',after,str(config))]:
        ran=subprocess.run([binary],input=':memory\n:q\n',text=True,capture_output=True,env=dict(os.environ,RNX_CONFIG=path,TERM='dumb'));assert ran.returncode==0
        conditions['memory'][label]=dict(stdout=ran.stdout,stderr=ran.stderr)
    for label,binary in [('before',before),('after',after)]:
        data=pathlib.Path(binary).read_bytes();conditions['binaries'][label]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    for cmd in [['rustc','--version'],['hyperfine','--version'],['uname','-a']]:conditions['versions'][' '.join(cmd)]=subprocess.check_output(cmd,text=True).strip()
    conditions['affinity_core']=4;conditions['config']=config.read_text();conditions['session_bound']='configured mean <= absent mean + 10 ms; local acceptance bound, not universal guarantee'
    (out/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
    cmd=['taskset','-c','4','hyperfine','-N','--input','probes/settings/quit.txt','--warmup','10','--runs','100','--export-json',str(out/'startup.json')]
    for name,args in commands:cmd+=['--command-name',name,shlex.join(args)]
    subprocess.run(cmd,check=True)
results={r['command']:r for r in json.loads((out/'startup.json').read_text())['results']}
assert results['session configured']['mean'] <= results['session after']['mean']+.010
