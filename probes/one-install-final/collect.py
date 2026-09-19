from common import *
import re,statistics as st
stock=json.loads((O/'stock-summary.json').read_text());launch=json.loads((O/'launch-summary.json').read_text());cost=json.loads((O/'cost-summary.json').read_text());assert json.loads((O/'stock-gate.json').read_text())['passed'];assert json.loads((O/'launch-gate.json').read_text())['passed']
for filename,expected in [('stock-samples.jsonl',2400),('launch-samples.jsonl',3360)]:
 rows=[json.loads(x) for x in (O/filename).read_text().splitlines()];assert len(rows)==expected
 if filename.startswith('stock'):keys=[(r['repeat'],r['sample'],r['mode'],r['kind']) for r in rows]
 else:keys=[(r['repeat'],r['sample'],r['mode'],r['kind'],r['route'],r['count']) for r in rows]
 assert len(keys)==len(set(keys))
assert len(json.loads((O/'profile-samples.json').read_text()))==720
reg={r['name']:r['status'] for r in json.loads((O/'regression.json').read_text())};assert all(status==0 for name,status in reg.items() if name!='root-clippy');assert not json.loads((O/'clippy-comparison.json').read_text())['added']
counts={}
for name in ['root-default','root-support','root-runner','tool-default','tool-support','adapters-postgres-tests','adapters-polars-tests','servers-http-postgres-tests']:
 counts[name]=sum(int(n) for n in re.findall(r'test result: ok\. (\d+) passed',(O/(name+'.log')).read_text()))
traces=json.loads((O/'traces.json').read_text());assert len(traces)==8 and all(t['attachment_compilation_trapped'] for t in traces)
for t in traces:
 if t['kind']=='git':assert t['git_source_opens']==0 and t['network']==False and len(t['execs'])==2
summary={'tests':counts,'stock':stock,'over_direct_ms':{k:{str(n):st.median(x['over_direct'] for x in launch if x['kind']==k and x['count']==n) for n in range(4)} for k in ['git','path']},'path_first_adapter_cells':[x for x in launch if x['kind']=='path' and x['count']==1],'costs':cost,'root_clippy':'15 retained diagnostics including test-only findings; none added versus baseline','no_source_reads_or_tools_in_git_launch':True,'notes':'headline medians combine run/eval/prompt and both repeats only for this compact view; full cells and spreads retained separately'}
save('summary.json',summary);print(json.dumps(summary['over_direct_ms'],indent=2));print('all closing evidence checks passed')
