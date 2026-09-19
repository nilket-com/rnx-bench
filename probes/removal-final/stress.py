"""Twelve concurrent support suites, with separate output and no retry filter."""
from pathlib import Path
import subprocess as sp,json,time
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/removal-final-0066/stress';O.mkdir(exist_ok=True)
p=sp.run(['cargo','test','--locked','--offline','--manifest-path',str(R/'tools/project/Cargo.toml'),'--features','test-support','--no-run','--message-format=json'],capture_output=True,text=True);assert p.returncode==0,p.stderr
bins=[json.loads(x)['executable'] for x in p.stdout.splitlines() if json.loads(x).get('reason')=='compiler-artifact' and json.loads(x).get('executable') and json.loads(x)['profile']['test']];assert len(bins)==1
jobs=[]
for i in range(12):
 f=(O/(str(i)+'.log')).open('w');jobs.append((sp.Popen([bins[0]],stdout=f,stderr=sp.STDOUT),f))
rows=[]
for i,(p,f) in enumerate(jobs):rows.append(dict(run=i,status=p.wait(timeout=300)));f.close()
(O/'results.json').write_text(json.dumps(rows,indent=2)+'\n');assert all(r['status']==0 for r in rows),rows
print('PASS twelve concurrent support suites')
