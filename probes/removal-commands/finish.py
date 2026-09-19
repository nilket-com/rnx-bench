from pathlib import Path
import hashlib,json,subprocess as sp,ast
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/removal-commands-0066'
d=json.loads((O/'build.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,v in d['sources_sha256'].items():assert sha(R/n)==v,n
for n,v in d['binaries'].items():assert sha(H/'target/bin'/('rnx-project-'+n))==v
for p in H.glob('*.py'):ast.parse(p.read_text())
for n in ['src','Cargo.toml','Cargo.lock','adapters','servers','kernel']:
 assert not sp.check_output(['git','-C',R,'diff','bafa2a0','--',n]),n
p=sp.run(['python3',R/'tools/project/scripts/notices.py','--check'],cwd=R,capture_output=True,text=True);assert p.returncode==0,p.stderr
assert len(json.loads((O/'matrix.json').read_text())['cases'])==42
assert json.loads((O/'contracts.json').read_text())['count']==52
assert json.loads((O/'rebuild.json').read_text())['compile_execs']>0
# No process may still execute a fixture binary or have a fixture working directory.
left=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdecimal():continue
 for name in ['exe','cwd']:
  try:
   target=(proc/name).resolve(strict=True)
   if target.is_relative_to(H/'target'):left.append((proc.name,name,str(target)))
  except (OSError,RuntimeError):pass
assert not left,left
mounts=Path('/proc/self/mountinfo').read_text();assert str(H/'target') not in mounts
(O/'finish.json').write_text(json.dumps(dict(source_and_binary_hashes_match=True,root_unchanged=True,notices=p.stdout.strip(),python_syntax=True,no_fixture_processes=True,no_fixture_mounts=True),indent=2)+'\n')
print('PASS final source, notices, evidence and cleanup checks')
