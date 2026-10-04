"""Bind delivery accounting to all complete warmup/measurement HTTP successes."""
import json,pathlib,statistics,sys
out=pathlib.Path(sys.argv[1]);rows=[json.loads(x) for x in (out/'results.jsonl').read_text().splitlines()]
assert len(rows)==6
medians={n:statistics.median(r['rps'] for r in rows if r['impl']==n) for n in ('off','requests')}
artifacts=[json.loads(p.read_text()) for p in sorted(out.glob('oha-*.json'))];assert len(artifacts)==12
successes=3
for a in artifacts:
 assert a['exit']==0
 if a['port']==18105:
  r=a['result'];assert not r['errorDistribution'];assert set(r['statusCodeDistribution'])=={'200'}
  successes+=r['statusCodeDistribution']['200']
log=json.loads((out/'requests-log-summary.json').read_text());delivered=log['events']['request']
summaries=[r for r in log['other_records'] if r['event']=='log_summary'];assert len(summaries)==1
dropped=summaries[0]['dropped'];assert delivered+dropped==successes,(delivered,dropped,successes)
s={'median_rps':medians,'percent':100*(medians['requests']/medians['off']-1),'delivered_requests':delivered,'dropped_requests':dropped,'all_http_successes_including_wire':successes}
(out/'summary.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s,indent=2))
