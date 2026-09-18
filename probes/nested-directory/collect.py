from pathlib import Path
import ast,json,hashlib,subprocess as sp
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/nested-directory-0065'
def read(p):return json.loads((O/p).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert len(read('matrix.json'))==36 and len(read('extra.json'))==16
assert read('checks.json')['complete'] and all(c['status']==0 for c in read('checks.json')['checks'])
assert '46 passed; 0 failed' in (O/'tests-default.log').read_text()
assert '47 passed; 0 failed' in (O/'tests-support.log').read_text()
assert len((O/'samples.jsonl').read_text().splitlines())==4500
assert len((O/'fallback-samples.jsonl').read_text().splitlines())==360
failures=read('gate.json')['failures'];assert not read('gate.json')['passed'] and len(failures)==6 and all(f['count']==1 for f in failures)
assert read('fallback.json')['inputs_restored'] and read('fallback.json')['lock_pair_receipt_unchanged']
prod=R/'tools/project/target/release/rnx-project';assert sha(prod)==sha(W/'reuse');assert b'NESTED_PAUSE_ROOT' not in prod.read_bytes()
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
changed=sp.check_output(['git','-C',R,'diff','--name-only','2bf4871'],text=True).splitlines();assert all(p.startswith('plans/') or p=='tools/project/src/fingerprint/reuse.rs' for p in changed),changed
(O/'conditions.json').write_text(json.dumps(dict(root_head=sp.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip(),baseline='2bf4871',source_sha256={str(p.relative_to(R)):sha(p) for p in sorted((R/'tools/project/src').rglob('*.rs'))},release_sha256=sha(prod),test_support_probe_sha256=sha(R/'tools/project/target/debug/rnx-project-assembly-probe'),scope='F2 only; no format, dependency, root runtime or stamp-vector change',outcome='STOP: floor passes, first-adapter increment above 1 ms; no post-measurement optimization'),indent=2)+'\n')
(O/'implementation.patch').write_bytes(sp.check_output(['git','-C',R,'diff','--binary','2bf4871','--','tools/project']))
print('PASS collection: 4500 headline / 360 fallback; stop on six first-adapter increments')
