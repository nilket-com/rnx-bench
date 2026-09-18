"""Summaries and retained bytes, after all timed processes have exited."""
from pathlib import Path
import json,statistics,hashlib,subprocess,ast
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/runtime-cost-0064';s=json.loads((W/'setup.json').read_text())
def save(name,value):(O/name).write_text(json.dumps(value,indent=2)+'\n')
rows=[]
for c in s['cells']:
 a=Path(c['artifact']);entry=a.parent.parent;paths=[entry,*entry.rglob('*')];files=[p for p in paths if p.is_file()]
 rows.append(dict(label=c['label'],files=len(files),logical_bytes=sum(p.stat().st_size for p in files),allocated_bytes=sum(p.stat().st_blocks*512 for p in paths),artifact_bytes=a.stat().st_size))
save('retained-assemblies.json',rows)
install=json.loads((O/'installation-summary.json').read_text());root=Path(s['installed']);paths=[root.parent,*root.parent.rglob('*')];install['entry']['allocated_tree_bytes']=sum(p.stat().st_blocks*512 for p in paths);install['entry']['directory_count']=sum(p.is_dir() for p in paths);save('installation-summary.json',install)
for n in [1,2]:
 cells=[c for c in s['cells'] if c['natives']==n];ids=[json.loads(json.loads(Path(c['manifest']).with_name('rnx.lock').read_text())['assembly']['identity']) for c in cells]
 assert ids[0]['main']==ids[1]['main'] and ids[0]['cargo_lock_sha256']==ids[1]['cargo_lock_sha256']
for name in ['attachments','describe']:
 data=json.loads((O/(name+'.json')).read_text());summary=[]
 for rep in range(2):
  for origin in ['checkout','installed']:
   for n in [1,2]:summary.append(dict(repeat=rep,origin=origin,natives=n,median_ms=statistics.median(r['ms'] for r in data if r['repeat']==rep and r['origin']==origin and r['natives']==n)))
 save(name+'-summary.json',summary)
save('setup.json',{k:v for k,v in s.items() if k!='env'})
conditions=dict(baseline=s['baseline'],ordinary_tool_sha256=hashlib.sha256(Path(s['tool']).read_bytes()).hexdigest(),matched_main_and_cargo_lock=True,platform=subprocess.check_output(['uname','-sm'],text=True).strip(),cpu=json.loads((O/'measurement.json').read_text())['cpu'],polars_threads=1,cold_builds='single unrestricted-CPU observations, registry cached and offline, separate fresh target per identity',first_checkout_build_qualification='recorded run overlapped isolated timing-tool compilation during setup; no speed comparison inferred from cold-build deltas',phase_sampling='started only after all four cold assemblies completed',artifact_sampling='started only after installation sampling completed',all_samples_retained=True)
left=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  args=(proc/'cmdline').read_bytes().split(b'\0');exe=args[0].decode() if args else ''
  if exe.startswith(str(W)+'/'):left.append(int(proc.name))
 except (OSError,UnicodeError):pass
assert not left,left;conditions['remaining_fixture_executables']=left
for p in H.glob('*.py'):ast.parse(p.read_text())
save('conditions.json',conditions)
