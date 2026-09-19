from common import *
import shutil,re
snap=O/'projects';snap.mkdir(exist_ok=True);projects={}
for row in json.loads((O/'real-journeys.json').read_text()):projects['git-polars-'+str(row['consumer'])]=Path(row['manifest']).parent
for name in ['real-combined','path-combined','tiny-a-clean','tiny-b-clean','mixed-app','legacy-app']:projects[name]=T/name
rows=[]
for name,base in projects.items():
 out=snap/name;out.mkdir(exist_ok=True);files={}
 for relative in ['rnx.toml','rnx.lock','rnx.Cargo.lock','.rnx/receipt.json','main.rn']:
  f=base/relative
  if f.exists():
   dest=out/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest);files[relative]=sha(f.read_bytes())
 rows.append({'project':name,'source':str(base),'files_sha256':files})
save('project-snapshots.json',rows)
checks=[]
for mode in ['root-default','root-support','root-runner','tool-default','tool-support']:
 text=(O/(mode+'.log')).read_text();counts=[c[:3] for c in re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; \d+ measured; (\d+) filtered out',text) if c[3]=='0'];assert counts
 checks.append({'configuration':mode,'passed':sum(int(c[0]) for c in counts),'failed':sum(int(c[1]) for c in counts),'ignored':sum(int(c[2]) for c in counts)})
save('suite-counts.json',checks)
print('Project lock pairs, receipts and suite counts archived',flush=True)
