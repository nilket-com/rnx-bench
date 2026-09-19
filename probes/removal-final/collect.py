from pathlib import Path
import json,statistics as st,re
H=Path(__file__).resolve().parent;B=H.parents[1];O=B/'results/removal-final-0066';rows=json.loads((O/'launch/summary.json').read_text());samples=[json.loads(v) for v in (O/'launch/samples.jsonl').read_text().splitlines()]
result={'overhead_by_count':[dict(count=n,**{v:st.median(r['over_direct'] for r in rows if r['count']==n and r['version']==v) for v in ['before','after']}) for n in range(4)],'first_adapter':[dict(mode=m,repeat=k,**{v:next(r['increment'] for r in rows if r['count']==1 and r['mode']==m and r['repeat']==k and r['version']==v) for v in ['before','after']}) for k in range(2) for m in ['run','eval','session']],'verify':[dict(version=v,repeat=k,median_ms=st.median(r['wall_ns']/1e6 for r in samples if r['route']=='verify' and r['version']==v and r['repeat']==k)) for v in ['before','after'] for k in range(2)],'test_counts':{}}
for name in ['root-default','root-support','root-combined','tool-default','tool-support']:
 s=(O/'regression'/(name+'.log')).read_text();counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; \d+ measured; 0 filtered out;',s);result['test_counts'][name]=dict(zip(['passed','failed','ignored'],[sum(int(r[i]) for r in counts) for i in range(3)]))
result['aggregation']='overhead table is median of six mode/repeat project-minus-direct medians; first-adapter cells are separate and unrounded here'
(O/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
