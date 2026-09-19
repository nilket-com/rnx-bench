from common import *
rows=[]
for path in ['adapters/postgres','adapters/polars','servers/http-postgres']:
 for command,args in [('fmt',['cargo','fmt','--manifest-path',path+'/Cargo.toml','--check']),('clippy',['cargo','clippy','--locked','--offline','--manifest-path',path+'/Cargo.toml','--all-targets','-j','4','--','-D','warnings'])]:
  p=run(args,ok=False);name=path.replace('/','-')+'-'+command;(O/(name+'.log')).write_bytes(p.stdout+p.stderr);rows.append({'name':name,'status':p.returncode,'args':args});
  if p.returncode:
   assert command=='clippy'
   unchanged=run(['git','-c','color.ui=false','diff','94f5f3f','--',path+'/src']).stdout==b''
   rows[-1]['source_byte_identical_to_baseline']=unchanged
   assert unchanged,name
  save('native-checks.json',rows)
print('native checks complete; retained baseline diagnostics separately')
