from pathlib import Path
import ast,hashlib,json,subprocess as sp
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/nested-product-0065';W=H/'target'
def read(p):return json.loads((O/p).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert len(read('matrix.json'))==36 and len(read('extra.json'))==16
assert read('checks.json')['complete'] and all(c['status']==0 for c in read('checks.json')['checks'])
assert '46 passed; 0 failed' in (O/'tests-default.log').read_text()
assert '47 passed; 0 failed' in (O/'tests-support.log').read_text()
assert len((O/'samples.jsonl').read_text().splitlines())==4500
assert len((O/'fallback-samples.jsonl').read_text().splitlines())==360
assert not read('gate.json')['passed'] and len(read('gate.json')['failures'])==6
assert read('fallback.json')['inputs_restored'] and read('fallback.json')['lock_pair_receipt_unchanged']
assert b'NESTED_PAUSE_ROOT' not in (W/'reuse').read_bytes()
prod=R/'tools/project/target/release/rnx-project';assert sha(prod)==sha(W/'reuse')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
changes=sp.check_output(['git','-C',R,'diff','--name-only','e6844b6'],text=True).splitlines();assert all(p.startswith(('tools/project/','plans/')) for p in changes)
assert not sp.check_output(['git','-C',R,'diff','e6844b6','--','tools/project/Cargo.toml','tools/project/Cargo.lock'])
(O/'conditions.json').write_text(json.dumps(dict(root_head=sp.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip(),baseline='e6844b6',source_sha256={str(p.relative_to(R)):sha(p) for p in sorted((R/'tools/project/src').rglob('*.rs'))},release_sha256=sha(prod),test_support_probe_sha256=sha(R/'tools/project/target/debug/rnx-project-assembly-probe'),pause_marker_absent_from_release=True,scope='tool only, no dependency or format change',outcome='STOP: zero-adapter floor improvement below 3 ms; no post-measurement implementation change'),indent=2)+'\n')
(O/'implementation.patch').write_bytes(sp.check_output(['git','-C',R,'diff','--binary','e6844b6','--','tools/project']))
print('PASS preserved stop: 4500 headline and 360 fallback samples; correctness checks pass')
