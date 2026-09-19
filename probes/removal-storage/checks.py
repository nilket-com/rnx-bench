"""Confirm the accepted product and all fixture consumers remain bounded to this gate."""
from pathlib import Path
import hashlib,json,subprocess as sp,ast
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/removal-storage-0066';W=H/'target/real'
d=json.loads((B/'results/removal-commands-0066/build.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,digest in d['sources_sha256'].items():assert sha(R/name)==digest,name
for mode,name in [('ordinary','rnx-project'),('support','rnx-project-support')]:assert sha(W/'bin'/name)==d['binaries'][mode]
assert not sp.check_output(['git','-C',R,'diff','06a295e','--','src','Cargo.toml','Cargo.lock','tools/project/src','tools/project/Cargo.toml','tools/project/Cargo.lock','adapters','servers','jupyter'])
for p in H.glob('*.py'):ast.parse(p.read_text())
rows=[]
for cmd in [['cargo','fmt','--manifest-path',str(R/'tools/project/Cargo.toml'),'--','--check'],['python3',str(R/'tools/project/scripts/notices.py'),'--check']]:
 p=sp.run(cmd,cwd=R,capture_output=True,text=True);assert p.returncode==0,(p.stdout,p.stderr);rows.append({'command':cmd,'output':p.stdout.strip()})
left=[]
for p in Path('/proc').iterdir():
 if not p.name.isdecimal():continue
 for field in ['exe','cwd']:
  try:
   q=(p/field).resolve(strict=True)
   if q.is_relative_to(H/'target'):left.append((p.name,field,str(q)))
  except (OSError,RuntimeError):pass
assert not left,left
assert str(H/'target') not in Path('/proc/self/mountinfo').read_text()
assert json.loads((O/'corrupt.json').read_text())['removal_succeeded']
j=json.loads((O/'journey.json').read_text());assert j['post_removal_default']['typed_query'] and j['polars_interruption']['killed_during_unlink']
(O/'checks.json').write_text(json.dumps(dict(product_revision='06a295e',product_sources_match_accepted=True,binaries=d['binaries'],launcher_sha256=sha(W/'bin/rnx'),checks=rows,no_fixture_processes=True,no_fixture_mounts=True,fixture_sha256={p.name:sha(p) for p in H.glob('*.py')}),indent=2)+'\n')
print('PASS product correspondence, syntax, notices and no remaining consumers')
