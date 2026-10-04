"""Fail closed on completeness, run association, exits, complete oha fields and occupancy."""
import importlib.util,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('probe',HERE/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
out=pathlib.Path(sys.argv[1]);rows=[json.loads(l) for l in (out/'results.jsonl').read_text().splitlines()]
loads=[r for r in rows if r['case']=='load']
expected={(n,rep,route,c,ka) for n in 'AB' for rep in range(3) for route,c,ka in m.CONDITIONS}
identities=[(r['impl'],r['rep'],r['route'],r['concurrency'],r['keepalive']) for r in loads]
assert len(identities)==len(expected) and set(identities)==expected
files=sorted(out.glob('oha-*.json'));assert len(files)==60
artifacts=[json.loads(p.read_text()) for p in files]
for i,a in enumerate(artifacts):
	assert a['exit']==0 and json.loads(a['stdout'])==a['result']
	m.b.validate(a['result'],a['concurrency'],False,None)
	assert a['seconds']==(3 if i%2==0 else 10)
for r in loads:
	m.b.validate({'summary':{'requestsPerSec':r['rps']},'latencyPercentiles':{'p50':r['p50_ms']/1000,'p99':r['p99_ms']/1000},'statusCodeDistribution':r['codes'],'errorDistribution':r['errors']},r['concurrency'],r['keepalive'],r.get('connections'))
# Bind each measured JSON to its row, in the driver's frozen traversal order.
j=0
for rep in range(3):
	for route,c,ka in m.CONDITIONS:
		for name in ('AB' if rep%2==0 else 'BA'):
			r=loads[j]
			for phase in [0,1]:
				a=artifacts[2*j+phase]
				assert (a['port'],a['route'],a['concurrency'],a['keepalive'],a['seconds'])==(m.b.PORTS[name],route,c,ka,3 if phase==0 else 10)
				expected=['taskset','-c',m.b.LOAD_CPUS,'oha','--no-tui','--output-format','json','-z',f"{a['seconds']}s",'-c',str(c),'-w','--http-version','1.1']
				if not ka:expected+=['--disable-keepalive']
				expected+=[f'http://127.0.0.1:{a["port"]}{route}']
				assert a['argv']==expected
			j+=1
			assert (r['impl'],r['rep'],r['route'],r['concurrency'],r['keepalive'])==(name,rep,route,c,ka)
			v=m.b.validate(a['result'],c,ka,r.get('connections'))
			assert all(r[k]==v[k] for k in v),(name,route,k)
print('30 exact conditions + 60 complete warm/measured artifacts, exits, row bindings and wire occupancy PASS')
