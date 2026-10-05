"""Supplemental independent clock; original timed samples remain unchanged."""
import json,os,pathlib,shlex,subprocess,sys
P=pathlib.Path(__file__).resolve().parent
O=pathlib.Path(sys.argv[1]).resolve()
c=json.loads((O/'conditions.json').read_text());os.sched_setaffinity(0,{c['machine']['cpu']})
rows=[json.loads(s) for s in (O/'samples.jsonl').read_text().splitlines()]
env=os.environ.copy();env.update(RNX_CONFIG=str(P/'target/no-config'),RNX_HISTORY=str(P/'target/history'),TERM='dumb')
argv=['hyperfine','-N','--warmup','5','--runs','50','--export-json',str(O/'hyperfine.json')]
commands={}
for name in ('build-print-default','print-metadata','print-obj','cached-print-default','true','python','rnx-eval'):
	row=next(r for r in rows if r['case']==name)
	commands[name]=row['commands'][0]
	argv+=['--command-name',name,shlex.join(commands[name])]
(O/'hyperfine-conditions.json').write_text(json.dumps({'commands':commands,'argv':argv,'purpose':'independent direct-exec timing check; existing output overwritten by rustc (still fresh compilation, no cache); no compile-and-run wrapper','affinity':[c['machine']['cpu']]},indent=2)+'\n')
r=subprocess.run(argv,env=env,capture_output=True,text=True,timeout=120)
(O/'hyperfine.txt').write_text(r.stdout.rstrip()+'\n'+r.stderr.rstrip()+'\n')
assert r.returncode==0,r.stderr
