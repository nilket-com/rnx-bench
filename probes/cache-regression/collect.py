"""Bind replay results to published sources and check the final evidence set."""
from pathlib import Path
import ast,hashlib,json,os,re,subprocess
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/cache-regression-0061'
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for name in ['checks','integrations','fixtures']:
 rows=json.loads((O/(name+'.json')).read_text());assert rows and all(r['status']==0 for r in rows),name
counts={}
for name in ['root-default','root-support','root-combined','tool-default','tool-support','tool-opt-in-integrations']:
 found=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored',(O/(name+'.log')).read_text())
 assert found,name
 counts[name]={key:sum(int(r[i]) for r in found) for i,key in enumerate(['passed','failed','ignored'])}
(O/'counts.json').write_text(json.dumps(counts,indent=2)+'\n')
head=subprocess.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip()
assert not subprocess.check_output(['git','-C',R,'diff','HEAD','--','tools/project/src'])
patch=subprocess.check_output(['git','-C',R,'-c','color.ui=false','diff','--binary','814d20f','HEAD','--','tools/project'])
(O/'commands/source.patch').write_bytes(patch)
for relative,patch_path in [('commands/conditions.json','source.patch'),('commands/publication-replay/conditions.json','../source.patch')]:
 p=O/relative;d=json.loads(p.read_text());d.update(implementation_revision=head,patch_baseline='814d20f',source_patch=patch_path,source_patch_sha256=hashlib.sha256(patch).hexdigest());p.write_text(json.dumps(d,indent=2)+'\n')
hashes={}
for name,p in [('stock',R/'target/release/rnx'),('tool',R/'tools/project/target/release/rnx-project'),('tool-support',R/'tools/project/target/debug/rnx-project')]:
 with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
 hashes[name]={'sha256':digest,'bytes':p.stat().st_size}
# Historical source snapshots/results must stay untouched by output redirection.
changed=subprocess.check_output(['git','-C',B,'diff','--name-only','HEAD'],text=True).splitlines()
assert all(p.startswith(('probes/cache-regression/','results/cache-regression-0061/')) for p in changed),changed
active=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)==os.getpid():continue
 try:exe=str((p/'exe').resolve())
 except OSError:continue
 if '/probes/cache-regression/target/' in exe or '/probes/cache-publication/target/' in exe:active.append({'pid':p.name,'exe':exe})
assert not active,active
conditions={'rnx_head':head,'bench_base':subprocess.check_output(['git','-C',B,'rev-parse','HEAD'],text=True).strip(),'binaries':hashes,'root_tests':'serial configurations, one test thread','tool_tests':'serial configurations, one test thread; opt-in integrations separately executed','windows':'MSVC type-check only; existing test-only UNIX_EPOCH warning; commands still refuse','accepted_bench_files_unchanged':True,'active_fixture_executables':active,'rustc':subprocess.check_output(['rustc','-Vv'],text=True)}
(O/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
print(json.dumps(counts,indent=2));print('PASS source provenance, retained results and final evidence checks')
