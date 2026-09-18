from pathlib import Path
import ast,json,hashlib,subprocess as sp,collections
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/nested-scoped-0065'
def read(p):return json.loads((O/p).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert len(read('matrix.json'))==36 and len(read('extra.json'))==16
assert len(read('roster.json'))==6 and len(read('untracked-repository.json'))==2
assert len(read('between-children.json')['observations'])==2
assert read('checks.json')['complete'] and all(c['status']==0 for c in read('checks.json')['checks'])
assert '46 passed; 0 failed' in (O/'tests-default.log').read_text()
assert '47 passed; 0 failed' in (O/'tests-support.log').read_text()
for filename,total,fields,cells in [('samples.jsonl',4500,['version','count','mode','route'],75),('fallback-samples.jsonl',360,['shape','route'],6),('profile-samples.jsonl',480,['count','mode'],8)]:
 rows=[json.loads(line) for line in (O/filename).read_text().splitlines()];assert len(rows)==total
 keys=[tuple(r[k] for k in fields+['repeat','sample']) for r in rows];assert len(set(keys))==len(keys)
 counts=collections.Counter(tuple(r[k] for k in fields+['repeat']) for r in rows);assert len(counts)==cells*2 and set(counts.values())=={30}
 assert all(r['wall_ns']>0 for r in rows)
 if filename.startswith('profile'):
  for r in rows:
   for p in r['inventory']:assert sum(p['phase_ns'].values())==p['wall_ns']
f=read('gate.json');assert not f['passed'] and len(f['failures'])==6 and all(x['count']==1 for x in f['failures'])
assert read('fallback.json')['inputs_restored'] and read('fallback.json')['lock_pair_receipt_unchanged']
assert read('launch.json')['files_restored'] and read('launch.json')['lock_pair_receipt_unchanged']
for r in read('roster.json'):
 assert r['git']==(3 if r['case']=='ignored-build-14000' else 3*(r['count']+1))
for r in read('profile.json')['summary']:
 assert r['phase_calls']['independent']==[1]
 if r['count']:assert r['phase_calls']['shared_rechecks']==[1] and r['phase_calls']['observation']==[886]
prod=R/'tools/project/target/release/rnx-project';assert sha(prod)==sha(W/'reuse')==sha(W/'ordinary')
assert read('measurement.json')['binaries']['reuse']['sha256']==sha(prod)
assert read('profile.json')['binaries']['profiled']==sha(W/'profiled')
assert b'RNX_INVENTORY_PROFILE' not in prod.read_bytes() and b'NESTED_PAUSE_ROOT' not in prod.read_bytes()
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
changed=sp.check_output(['git','-C',R,'diff','--name-only','1a15f9d'],text=True).splitlines();allowed={'tools/project/src/fingerprint/reuse.rs','tools/project/src/fingerprint/trace.rs','tools/project/src/fingerprint/tests.rs','tools/project/README.md'};assert all(p.startswith('plans/') or p in allowed for p in changed),changed
(O/'conditions.json').write_text(json.dumps(dict(root_head=sp.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip(),baseline='1a15f9d',source_sha256={str(p.relative_to(R)):sha(p) for p in sorted((R/'tools/project/src').rglob('*.rs'))},release_sha256=sha(prod),test_support_release_sha256=sha(W/'profiled'),test_support_probe_sha256=sha(R/'tools/project/target/debug/rnx-project-assembly-probe'),scope='F3/F4 and test-support exclusive clocks; no format, dependency, root runtime or persistent-cache change',outcome='STOP: six first-adapter increments above 1 ms; attribution retained without post-measurement optimization'),indent=2)+'\n')
(O/'implementation.patch').write_bytes(sp.check_output(['git','-C',R,'diff','--binary','1a15f9d','--','tools/project']))
print('PASS collection: 4500 headline / 360 practical / 480 attribution; six first-adapter failures retained')
