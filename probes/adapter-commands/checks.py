"""Serial release checks; each command's complete output and status is retained."""
from pathlib import Path
import json,os,subprocess,time
H=Path(__file__).resolve().parent; B=H.parents[1]; R=B.parent/'rnx'; O=B/'results/adapter-commands-0062/regression'
O.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,TERM='xterm-256color')
rows=[]
commands=[
 ('root-fmt',['cargo','fmt','--all','--','--check']),
 ('tool-fmt',['cargo','fmt','--manifest-path','tools/project/Cargo.toml','--all','--','--check']),
 ('root-default',['cargo','test','--locked','--offline','--','--test-threads=1']),
 ('root-support',['cargo','test','--locked','--offline','--features','test-support','--','--test-threads=1']),
 ('root-combined',['cargo','test','--locked','--offline','--features','test-support,server-runtime,project-sources','--','--test-threads=1']),
 ('root-notices',['bash','scripts/third-party-notices.sh','--check']),
 ('root-release',['cargo','build','--locked','--offline','--release','--bin','rnx']),
 ('root-selfcheck',[str(R/'target/release/rnx'),'selfcheck']),
 ('tool-default',['cargo','test','--locked','--offline','--manifest-path','tools/project/Cargo.toml','--','--test-threads=1']),
 ('tool-support',['cargo','test','--locked','--offline','--manifest-path','tools/project/Cargo.toml','--features','test-support','--','--test-threads=1']),
 ('tool-clippy-default',['cargo','clippy','--locked','--offline','--manifest-path','tools/project/Cargo.toml','--all-targets','--','-D','warnings']),
 ('tool-clippy-support',['cargo','clippy','--locked','--offline','--manifest-path','tools/project/Cargo.toml','--all-targets','--features','test-support','--','-D','warnings']),
 ('tool-notices',['python3','tools/project/scripts/notices.py','--check']),
 ('tool-windows',['cargo','check','--locked','--offline','--manifest-path','tools/project/Cargo.toml','--all-targets','--features','test-support','--target','x86_64-pc-windows-msvc']),
]
for name,cmd in commands:
 start=time.monotonic()
 with (O/(name+'.log')).open('w') as f:p=subprocess.run(cmd,cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
 row={'name':name,'command':cmd,'status':p.returncode,'seconds':time.monotonic()-start};rows.append(row)
 (O/'checks.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(name,p.returncode,flush=True)
 assert p.returncode==0,row
