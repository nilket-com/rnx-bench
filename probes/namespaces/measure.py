#!/usr/bin/env python3
"""0049: explicit old/new source, equal behavior before process-level timing."""
import hashlib,json,os,pathlib,shlex,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/namespaces-0049';OUT.mkdir(parents=True,exist_ok=True)
before,after=[str(pathlib.Path(p).resolve()) for p in sys.argv[1:3]]
os.chdir(ROOT)
result={'binaries':{},'sources':{},'outputs':{},'memory':{},'versions':{},'conditions':{'core':4,'warmups':10,'runs':100}}
with tempfile.TemporaryDirectory(prefix='rnx namespace ') as d:
 env=dict(os.environ,TERM='xterm',RNX_CONFIG=d+'/absent',RNX_HISTORY=d+'/history')
 for k in list(env):
  if k.startswith('RNX_TEST_') or k in ['RNX_MEMORY_CEILING','NO_COLOR']:env.pop(k,None)
 commands=[]
 for label,binary in [('before',before),('after',after)]:
  data=pathlib.Path(binary).read_bytes();result['binaries'][label]={'path':binary,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
  parse='host::json_parse' if label=='before' else 'json::parse'
  stringify='host::json_stringify' if label=='before' else 'json::stringify'
  source=(ROOT/'scripts/json.rn').read_text().replace('json::stringify',stringify)
  file=OUT/f'json-{label}.rn';file.write_text(source)
  result['sources'][label]={'path':str(file.relative_to(ROOT)),'sha256':hashlib.sha256(source.encode()).hexdigest()}
  child='host::process("/bin/true", [], 30000)?.code' if label=='before' else 'process::run("/bin/true", [], #{timeout_ms:30000})?.code'
  cases=[('version',['version']),('help',['help']),('eval',['eval','42']),('run',['run','scripts/bare.rn']),('json',['run',str(file)]),('child',['eval',child])]
  values=['18446744073709551615','-9223372036854775808','18446744073709551616','-9223372036854775809','-0','null','{"a":1,"a":2}','{\n"x":\n}']
  for i,v in enumerate(values):cases.append((f'parse-{i}',['eval',f'[{parse}({json.dumps(v)})]']))
  for i,v in enumerate(['let v=[]; v.push(v); '+stringify+'(v)', stringify+'(|| 1)',stringify+'(18446744073709551615u64)']):cases.append((f'write-{i}',['eval','[{ '+v+' }]']))
  for name,args in cases:
   cmd=[binary,*args];r=subprocess.run(cmd,capture_output=True,env=env,timeout=15)
   # All refusal payloads are kept as Result values to avoid intentionally
   # changed source excerpts and caret columns in propagated diagnostics.
   assert r.returncode==0,(name,r.stderr)
   result['outputs'][name+' '+label]={'argv':args,'stdout':r.stdout.decode(),'stderr':r.stderr.decode(),'exit':r.returncode}
   if name in ['version','eval','run','json','child']:commands.append((name+' '+label,cmd))
  r=subprocess.run([binary,'--no-splash'],input=b':memory\n:q\n',capture_output=True,env=env,timeout=10);assert r.returncode==0
  result['memory'][label]={'stdout':r.stdout.decode(),'stderr':r.stderr.decode(),'exit':r.returncode}
 for key,old in list(result['outputs'].items()):
  if key.endswith(' before'):
   new=result['outputs'][key[:-7]+' after']
   for field in ['stdout','stderr','exit']:assert old[field]==new[field],(key,field,old,new)
 for cmd in [['rustc','--version'],['cargo','--version'],['hyperfine','--version'],['uname','-a']]:result['versions'][' '.join(cmd)]=subprocess.check_output(cmd,text=True).strip()
 result['commands']=commands
 (OUT/'conditions.json').write_text(json.dumps(result,indent=2)+'\n')
 cmd=['taskset','-c','4','hyperfine','-N','--warmup','10','--runs','100','--export-json',str(OUT/'timings.json')]
 for name,args in commands:cmd+=['--command-name',name,shlex.join(args)]
 subprocess.run(cmd,env=env,check=True)
