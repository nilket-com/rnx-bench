"""Check provenance, replay completeness and process cleanup before review."""
from pathlib import Path
import ast,hashlib,json,os,re,subprocess as sp
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/runtime-final-0064'
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for p in [O/'regression/checks.json',O/'scope/integrations.json',*(O/(n+'-checks.json') for n in ['contracts','journey','cache']),O/'cache/fixtures.json']:
 rows=json.loads(p.read_text());assert rows and all(row['status']==0 for row in rows),p
confirm=O/'repair-confirm-checks.json'
if confirm.exists():assert all(r['status']==0 for r in json.loads(confirm.read_text()))
counts={}
for name in ['root-default','root-support','root-combined','tool-default','tool-support']:
 text=(O/'regression'/(name+'.log')).read_text();found=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored',text);assert found
 counts[name]={key:sum(int(r[i]) for r in found) for i,key in enumerate(['passed','failed','ignored'])}
(O/'counts.json').write_text(json.dumps(counts,indent=2)+'\n')
state=json.loads((O/'source-state.json').read_text());head=state['measured_head']
patch=(O/'source.patch').read_bytes()
tool_patch=sp.check_output(['git','-C',R,'diff','--no-color','--binary',state['patch_baseline'],'--','tools/project/src'])
assert hashlib.sha256(tool_patch).hexdigest()==state['tool_patch_sha256'],'product source changed during fixtures'
binaries={}
for name,p in [('stock',R/'target/release/rnx'),('tool',R/'tools/project/target/release/rnx-project'),('tool-support',R/'tools/project/target/debug/rnx-project'),('installed-stock',H/'target/installed/bin/rnx'),('installed-tool',H/'target/installed/bin/rnx-project')]:
 with p.open('rb') as f:d=hashlib.file_digest(f,'sha256').hexdigest()
 binaries[name]=dict(sha256=d,bytes=p.stat().st_size)
# Keep historical results byte-identical. All new script/output paths are explicit.
changed=sp.check_output(['git','-C',B,'diff','--name-only','HEAD'],text=True).splitlines();assert all(p.startswith(('probes/runtime-final/','results/runtime-final-0064/')) for p in changed),changed
active=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)==os.getpid():continue
 try:
  exe=os.readlink(p/'exe');args=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
 except OSError:continue
 if '/probes/runtime-final/target/' in exe or ('postgres' in exe and '/probes/runtime-final/' in args):active.append(dict(pid=p.name,exe=exe))
assert not active,active
conditions=dict(implementation_commit=sp.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip(),baseline=state['patch_baseline'],measured_head=head,source_patch='source.patch',patch_sha256=hashlib.sha256(patch).hexdigest(),bench_baseline=sp.check_output(['git','-C',B,'rev-parse','HEAD'],text=True).strip(),binaries=binaries,accepted_bench_files_unchanged=True,active_fixture_executables=active,windows='GNU root and MSVC tool type-check only; no Windows execution',rustc=sp.check_output(['rustc','-Vv'],text=True),source_scope='published baseline plus patch; later plan/evidence text not part of measured snapshot')
(O/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
print(json.dumps(counts,indent=2));print('PASS final source, checks and process accounting')
