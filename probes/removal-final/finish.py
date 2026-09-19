from pathlib import Path
import json,subprocess as sp,hashlib,ast
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/removal-final-0066'
for p in H.glob('*.py'):ast.parse(p.read_text())
old=sp.check_output(['git','-C',R,'show','021f401:tools/project/src/handshake.rs'],text=True);new=(R/'tools/project/src/handshake.rs').read_text()
a=old.index('async fn read(');z=old.index('let result = tokio::time::timeout',a);old_reader=old[a:z]
a=new.index('async fn read(');z=new.index('pub(crate) fn check',a);new_reader=new[a:z]
normalize=lambda x:'\n'.join(v.strip() for v in x.splitlines() if v.strip())
assert normalize(old_reader)==normalize(new_reader)
old_rest=old.replace(old[old.index('\t\t\tasync fn read('):old.index('\t\t\tlet result = tokio::time::timeout')],'')
new_rest=new[:new.index('async fn read(')]+new[new.index('pub(crate) fn check'):new.index('#[cfg(test)]')]
assert normalize(old_rest)==normalize(new_rest)
assert new.count('Duration::from_secs(1)')==1
assert all(v['status']==0 for v in json.loads((O/'regression/checks.json').read_text()))
assert len(json.loads((O/'stress/results.json').read_text()))==12 and all(v['status']==0 for v in json.loads((O/'stress/results.json').read_text()))
assert len(json.loads((O/'launch/first-adapter.json').read_text()))==12
assert json.loads((O/'launch/measurement.json').read_text())['samples']==3000
assert len(json.loads((O/'costs/measurements.json').read_text()))==3
for name in ['contracts-checks.json','supplement.json','removal-replay.json']:assert all(r['status']==0 for r in json.loads((O/name).read_text()))
assert len(json.loads((O/'installed/results.json').read_text())['sessions'])==2
left=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdecimal():continue
 for name in ['exe','cwd']:
  try:
   p=(proc/name).resolve(strict=True)
   if p.is_relative_to(H/'target'):left.append((proc.name,name,str(p)))
  except (OSError,RuntimeError):pass
assert not left,left
assert str(H/'target') not in Path('/proc/self/mountinfo').read_text()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for v in json.loads((O/'binaries.json').read_text()).values():assert sha(Path(v['path']))==v['sha256']
(O/'finish.json').write_text(json.dumps(dict(reader_body_unchanged=True,remaining_production_handshake_unchanged=True,one_second_bound_unchanged=True,no_fixture_processes=True,no_fixture_mounts=True,fixture_sha256={p.name:sha(p) for p in H.glob('*.py')},tool_source_sha256={str(p.relative_to(R)):sha(p) for p in (R/'tools/project/src').rglob('*.rs')}),indent=2)+'\n')
print('PASS closing correspondence, retained results and cleanup')
