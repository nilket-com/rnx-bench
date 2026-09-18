"""Verify closing evidence without rewriting any accepted gate-5 result."""
from pathlib import Path
import json,subprocess as sp,hashlib,re,collections
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/inventory-final-0065'
def read(path):return json.loads((O/path).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=read('regression/checks.json');assert len(checks)==13 and all(r['status']==0 for r in checks)
assert read('scope/scope.json')['protected_diff_empty'] and read('scope/scope.json')['default_graph_equal']
assert all(r['status']==0 for r in read('scope/integrations.json'))
assert all(r['status']==0 for r in read('contracts-checks.json'))
assert len(read('supplement.json'))==5 and all(r['status']==0 for r in read('supplement.json'))
counts={}
for name in ['root-default','root-support','root-combined']:
 rows=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', (O/'regression'/(name+'.log')).read_text());assert rows;counts[name]=sum(int(r[0]) for r in rows);assert all(r[1]=='0' for r in rows)
for name,n in [('tool-default',46),('tool-support',47)]:assert f'{n} passed; 0 failed; 2 ignored' in (O/'regression'/(name+'.log')).read_text()
for filename,total,fields,cells in [('headline/samples.jsonl',4500,['version','count','mode','route'],75),('topology-samples.jsonl',6480,['shape','count','mode','route'],108)]:
 rows=[json.loads(s) for s in (O/filename).read_text().splitlines()];assert len(rows)==total
 keys=[tuple(r[k] for k in fields+['repeat','sample']) for r in rows];assert len(set(keys))==total
 sizes=collections.Counter(tuple(r[k] for k in fields+['repeat']) for r in rows);assert len(sizes)==2*cells and set(sizes.values())=={30};assert all(r['wall_ns']>0 for r in rows)
assert read('topology-measurement.json')['inputs_restored']
assert len(read('topology-counters.json'))==18
assert len(read('roster/roster.json'))==6
attach=[json.loads(s) for s in (O/'attachment/attachment-samples.jsonl').read_text().splitlines()];assert len(attach)==120
assert read('attachment/attachment-summary.json')['compiler_trap_positive_control'] and read('attachment/attachment-summary.json')['full_artifact_hash']
assert read('attachment/real.json')['shared_journey'] and read('attachment/real.json')['override_journey']
journey=read('installed/matrix.json');assert journey['cleanup']['all_gone'] and journey['second_scratch']['compilation_trapped'] and journey['absolute']['typed_query'] and journey['relative']['typed_query']
assert read('installed/unavailable-path-check.json')['original_absent']
assert all(not Path('/proc',str(pid)).exists() for pid in journey['cleanup']['session_pids']+[journey['cleanup']['postmaster']])
old=B/'results/nested-position-0065';assert json.loads((old/'gate.json').read_text())['failures'][0]['increment']>1
# The accepted miss and every published sample remain byte-identical.
for rel in ['gate.json','samples.jsonl','summary.json']:
 expected=sp.check_output(['git','-C',B,'show','96a63ca:results/nested-position-0065/'+rel]);assert (old/rel).read_bytes()==expected
source={str(p.relative_to(R)):sha(p) for p in sorted((R/'tools/project/src').rglob('*.rs'))};assert source==json.loads((old/'conditions.json').read_text())['source_sha256']
assert sha(W/'tool')==json.loads((old/'measurement.json').read_text())['binaries']['reuse']['sha256']==sha(W/'reuse')
assert not sp.check_output(['git','-C',R,'diff','4855dbd','--','src','Cargo.toml','Cargo.lock','adapters','servers','jupyter','tools/project/src','tools/project/Cargo.toml','tools/project/Cargo.lock'])
summary=read('headline/summary.json');first=[r for r in summary if r['version']=='reuse' and r['count']==1];assert len(first)==6
conditions=dict(source_baseline='4855dbd',measured_head=sp.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip(),production_unchanged=True,source_sha256=source,binaries={str(p):sha(p) for p in [W/'tool',R/'target/release/rnx',W/'installed/bin/rnx-project',W/'installed/bin/rnx',W/'b3']},root_test_counts=counts,tool_test_counts={'default':46,'test-support':47},headline_first_adapter=first,headline_gate=read('headline/gate.json'),accepted_gate5_miss_unchanged=True,qualification='gate 5 accepted with its original 1.016205 ms miss; threshold unchanged and gate 6 reports fresh results separately',windows='not executed or rechecked',cleanup='installed sessions and private postmaster gone; per-fixture process ownership assertions retained; all cache entries retained')
(O/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
(O/'tool-source.patch').write_bytes(sp.check_output(['git','-C',R,'diff','--binary','4855dbd','--','tools/project/src']))
print('PASS closing collection',counts,'4500 headline / 6480 topology / 120 full-hash attachment samples')
