#!/usr/bin/env python3
"""Derive counts and timing medians from retained raw logs, without altering them."""
import json,pathlib,re
OUT=pathlib.Path(__file__).resolve().parents[2]/'results/project-regression-0057'
report={'suites':{},'stock_medians_ms':{}}
for name in ['default','test-support','all-features','tool-tests','tool-tests-feature']:
    rows=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored',(OUT/(name+'.log')).read_text());assert rows,name
    report['suites'][name]=dict(zip(['passed','failed','ignored'],[sum(int(r[i]) for r in rows) for i in range(3)]))
for kind in ['version','help','run','eval','json']:
    values=[]
    for i in (1,2):
        data=json.loads((OUT/f'startup-{i}-{kind}.json').read_text());v={r['command']:r['median']*1000 for r in data['results']};v['change_percent']=100*(v['after']/v['before']-1);values.append(v)
    report['stock_medians_ms'][kind]=values

def diagnostics(name):
    return sorted(m.groups() for m in re.finditer(r'^(warning|error): (.+)\n\s+--> (.+)',(OUT/name).read_text(),re.M))
before=diagnostics('before-clippy-features.log');after=diagnostics('root-clippy-features.log');assert before==after
report['root_clippy']={'baseline_equal':True,'findings':after,'status':'fails on existing deny-by-default permission literals; strict mode also fails existing warnings; no suppressions applied'}
before=(OUT/'default-tree-before.txt').read_text().replace('/tmp/rnx-0057-startup-before','ROOT');after=(OUT/'default-tree-after.txt').read_text().replace('/home/me/work/rnx','ROOT');assert before==after
report['default_graph_equal']=True
report['comparison_cases']=json.loads((OUT/'comparison.json').read_text())['equal_cases']
report['project_cost']=json.loads((OUT/'project-cost.json').read_text())
(OUT/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='root_clippy'},indent=2))
