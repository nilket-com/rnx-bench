#!/usr/bin/env python3
"""Matched process timings, exact output gate, hashes and command provenance."""
import hashlib,json,os,pathlib,shlex,subprocess,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[2]
os.chdir(root)
before,after=map(lambda p:str(pathlib.Path(p).resolve()),sys.argv[1:3])
out=root/'results/numbering_0040'
commands=[];outputs=[]
for name,args in [('version',['version']),('help',['help']),('eval',['eval','42']),('run',['run','scripts/bare.rn']),('json',['run','scripts/json.rn'])]:
    pair=[]
    for label,binary in [('before',before),('after',after)]:
        cmd=[binary,*args];commands.append((name+' '+label,cmd))
        ran=subprocess.run(cmd,capture_output=True)
        assert ran.returncode==0,ran.stderr
        pair.append((ran.returncode,ran.stdout,ran.stderr))
        outputs.append(dict(name=name+' '+label,stdout=ran.stdout.decode(),stderr=ran.stderr.decode(),exit=ran.returncode))
    assert pair[0]==pair[1],(name,pair)
conditions=dict(commands=commands,outputs=outputs,binaries={},versions={})
for label,binary in [('before',before),('after',after)]:
    data=pathlib.Path(binary).read_bytes()
    conditions['binaries'][label]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
for cmd in [['rustc','--version'],['hyperfine','--version'],['uname','-a']]:
    conditions['versions'][' '.join(cmd)]=subprocess.check_output(cmd,text=True).strip()
conditions['affinity_core']=4
conditions['memory']={}
with tempfile.TemporaryDirectory() as d:
    for label,binary in [('before',before),('after',after)]:
        p=subprocess.run([binary],input=':memory\n:quit\n',capture_output=True,text=True,env=dict(os.environ,TERM='dumb',RNX_HISTORY=d+'/'+label))
        assert p.returncode==0
        conditions['memory'][label]=dict(stdout=p.stdout,stderr=p.stderr)
(out/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
cmd=['taskset','-c','4','hyperfine','-N','--warmup','10','--runs','100','--export-json',str(out/'startup.json')]
for name,args in commands: cmd += ['--command-name',name,shlex.join(args)]
subprocess.run(cmd,check=True)
