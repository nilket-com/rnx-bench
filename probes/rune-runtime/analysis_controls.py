"""Mutate retained observations independently; agreeing corruptions must not report PASS."""
import json,pathlib,sys,tempfile,os
from analyse import analyse
out=pathlib.Path(sys.argv[1]).resolve();analyse(out)
mutations={
 'clock-failed':('clock-preflight.json',lambda v:v['true'].update(passed=False)),
 'clock-forged-pass':('clock-preflight.json',lambda v:v['true'].update(reference_ns=1e12,passed=True)),
 'case-missing':('cases.json',lambda v:v.pop()),
 'reuse-missing':('reused-calls.json',lambda v:v.pop()),
 'profile-missing':('profile.json',lambda v:v.pop()),
 'profile-duplicate':('profile.json',lambda v:v.__setitem__(0,v[1])),
 'inventory-altered':('profile.json',lambda v:v[0]['rows'][0]['inventory'].append('forged:function')),
 'profile-stage-missing':('profile.json',lambda v:next(r for r in v if r['enabled'])['rows'][0]['rows'].pop()),
 'overhead-forged':('profile-overhead.json',lambda v:v.update(ratio=0.01)),
 'plain-nonfinite':('unmodified-context.json',lambda v:v[0].update(context_ns=float('nan'))),
 'counter-missing':('counters.json',lambda v:v.pop()),
 'counter-forged':('counters.json',lambda v:v[0]['counts'].update(instructions=1)),
 'allocation-forged':('allocations.json',lambda v:v[0].update(calls=0)),
 'rss-missing':('rss.json',lambda v:v.pop()),
}
passed=[]
mutations.update({'sample-nonfinite':('samples.jsonl',lambda v:v[0].update(ns=float('nan'))),'sample-forged-positive':('samples.jsonl',lambda v:v[0].update(ns=v[0]['ns']+1)),'sample-missing':('samples.jsonl',lambda v:v.pop())})
for name,(file,change) in mutations.items():
 with tempfile.TemporaryDirectory(prefix='rune-analysis-controls-') as d:
  p=pathlib.Path(d)
  for f in out.iterdir():
   if f.is_dir():
    import shutil
    shutil.copytree(f,p/f.name,copy_function=os.link)
   elif f.is_file() and f.name not in ('analysis.json','REPORT.md','baseline-reproduction.json','analysis-controls.json'): (p/f.name).symlink_to(f)
  v=[json.loads(line) for line in (out/file).read_text().splitlines()] if file.endswith('.jsonl') else json.loads((out/file).read_text());change(v);(p/file).unlink();(p/file).write_text(''.join(json.dumps(row)+'\n' for row in v) if file.endswith('.jsonl') else json.dumps(v))
  try:analyse(p)
  except (AssertionError,KeyError,ValueError):passed.append(name)
  else:raise RuntimeError('accepted corrupt evidence: '+name)
(out/'analysis-controls.json').write_text(json.dumps(passed,indent=2)+'\n')
print('PASS:',len(passed),'retained-evidence corruptions refused')
