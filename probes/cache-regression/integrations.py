"""Run the two opt-in tool integrations against explicitly named real inputs."""
from pathlib import Path
import os,subprocess,json
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/cache-regression-0061'
env=dict(os.environ,TERM='xterm-256color',RNX_GATE2_BINARY=str(R/'target/debug/rnx'),
         RNX_GATE3_REPO=str(R),RNX_GATE3_INVENTORY=str(O/'native-inventory.json'))
commands=[('root-source-feature-build',['cargo','build','--locked','--offline','--features','project-sources','--bin','rnx']),
          ('tool-opt-in-integrations',['cargo','test','--locked','--offline','--manifest-path','tools/project/Cargo.toml','--features','test-support','--','--ignored','--test-threads=1','--nocapture'])]
rows=[]
for name,cmd in commands:
 with (O/(name+'.log')).open('w') as f:p=subprocess.run(cmd,cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 rows.append({'name':name,'command':cmd,'status':p.returncode});(O/'integrations.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(name,p.returncode,flush=True);assert p.returncode==0,name
