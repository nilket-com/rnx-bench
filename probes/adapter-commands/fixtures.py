"""Replay accepted fixtures without overwriting their published results."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/adapter-commands-0062/regression'
records=[]
def replay(relative,transform=lambda s:s):
 p=B/'probes'/relative;s=transform(p.read_text());dest=O/'scripts'/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(s)
 log=O/(relative.replace('/','-')+'.log')
 # Keep the fixture's original __file__: its ignored build directories and
 # sibling helper imports stay at their established locations.
 loader='import sys;sys.dont_write_bytecode=True;exec(compile(open(sys.argv[1]).read(),sys.argv[2],"exec"),{"__name__":"__main__","__file__":sys.argv[2]})'
 with log.open('w') as f:result=subprocess.run(['python3','-c',loader,str(dest),str(p)],cwd=B,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
 records.append({'source':relative,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'replay':str(dest.relative_to(O)),'status':result.returncode})
 (O/'fixtures.json').write_text(json.dumps(records,indent=2)+'\n')
 print(relative,result.returncode,flush=True)
 assert result.returncode==0,(relative,log)

commands=O/'commands';commands.mkdir(exist_ok=True)
def redirect(s):return s.replace('results/cache-commands-0061','results/adapter-commands-0062/regression/commands')
for name in ['build.py','check.py','replay.py','polars_override.py','publication_replay.py']:
 replay('cache-commands/'+name,redirect)
# Rebuild ordinary release separately; no simultaneous configuration changes.
with (O/'tool-release.log').open('w') as f:
 subprocess.run(['cargo','build','--locked','--offline','--release','--manifest-path',str(R/'tools/project/Cargo.toml'),'--bin','rnx-project'],stdout=f,stderr=subprocess.STDOUT,check=True)
replay('cache-commands/ordinary.py',redirect)

legacy=B/'probes/cache-commands/target/legacy-tool'
workflow=O/'workflow';workflow.mkdir(exist_ok=True)
def old_workflow(s):
 s=s.replace("OUT=BENCH/'results/project-workflow-0057'","OUT=BENCH/'results/adapter-commands-0062/regression/workflow'")
 old="return [str(TOOL),op,'--manifest'"
 assert old in s
 return s.replace(old,"return [("+repr(str(legacy))+" if op=='lock' else str(TOOL)),op,'--manifest'")
replay('project-workflow/check.py',old_workflow)

# Real PostgreSQL workflow on a fresh private shared cache. No local target
# seeding: the original fixture's old per-project cache is irrelevant here.
def postgres(s):
 s=s.replace("OUT=BENCH/'results/project-workflow-0057'","OUT=BENCH/'results/adapter-commands-0062/regression/workflow'")
 s=s.replace("WORK=HERE/'target/real'","WORK=BENCH/'probes/adapter-commands/target/regression/postgres'")
 start=s.index('# Seed only compilation cache.')
 end=s.index('sys.path.insert',start)
 s=s[:start]+"ENV['RNX_PROJECT_CACHE']=str(BENCH/'probes/adapter-commands/target/regression/postgres-cache')\n"+s[end:]
 return s
replay('project-workflow/postgres.py',postgres)
print('PASS command, publication, legacy, verification, interactive and PostgreSQL fixture replays',flush=True)
