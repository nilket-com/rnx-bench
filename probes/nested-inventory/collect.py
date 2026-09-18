from pathlib import Path
import ast,json,hashlib,subprocess as sp,difflib,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';P=H/'target/tool/tools/project';O=B/'results/nested-inventory-0065'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads((O/p).read_text())
assert len(read('matrix.json'))==36 and len(read('extra.json'))==16
assert len(read('migration/matrix.json'))==30
assert read('checks.json')['complete'] and all(x['status']==0 for x in read('checks.json')['checks'])
assert read('launch.json')['files_restored'] and read('recovery.json')['printed_command_executed']
assert '46 passed; 0 failed' in (O/'probe-tests.log').read_text()
assert 'error:' not in (O/'probe-clippy.log').read_text()
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
# Archive the effective modified modules plus the unchanged dependency lock.
S=O/'source';S.mkdir(exist_ok=True);patch=[]
for rel in ['src/fingerprint.rs','src/fingerprint/candidate.rs','src/inventory.rs','src/trace.rs','src/nested_probe.rs','src/main.rs','src/lib.rs','src/assembly_probe.rs','Cargo.toml','Cargo.lock']:
 q=S/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((P/rel).read_bytes())
 old=sp.run(['git','-C',R,'show','7b0bb65:tools/project/'+rel],capture_output=True).stdout.decode()
 patch.extend(difflib.unified_diff(old.splitlines(keepends=True),q.read_text().splitlines(keepends=True),fromfile='a/tools/project/'+rel,tofile='b/tools/project/'+rel))
assert (S/'Cargo.lock').read_bytes()==sp.check_output(['git','-C',R,'show','7b0bb65:tools/project/Cargo.lock'])
(O/'candidate.patch').write_text(''.join(patch))
prod=R/'tools/project/target/release/rnx-project'
(O/'provenance.json').write_text(json.dumps(dict(base='7b0bb65',root_head=sp.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip(),candidate_sources={str(p.relative_to(P)):sha(p) for p in sorted((P/'src').rglob('*.rs'))},binaries={str(p):sha(p) for p in [prod,P/'target/release/nested-probe',P/'target/release/rnx-project']},product_f1_sha256=sha(R/'tools/project/src/runtime_install/unix/legacy.rs'),product_reuse_enabled=False),indent=2)+'\n')
summary=[]
for row in read('extra.json'):
 if row['case'].startswith('real-roster'):
  def counts(r):return dict(git=sum('git' in e for e in r['events']),reads=sum('read' in e for e in r['events']))
  summary.append(dict(adapters=int(row['case'][-1]),oracle=counts(row['oracle']),candidate=counts(row['candidate']),trees=[dict(root=t['root'],files=len(t['files']),bytes=sum(f['bytes'] for f in t['files']),blake3=t['blake3']) for t in row['candidate']['answer']['Ok']]))
(O/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('PASS collection: 36 matrix, 16 topology/roster, 30 migration, F1 and workflow')
