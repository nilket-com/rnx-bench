"""Separate interleaved product logging cost, same CPU placement and workload, drained files."""
import importlib.util,json,pathlib,subprocess,sys
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('host_bench',HERE/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
b=m.b
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
rows=[];procs={};logs={};serial=0
original=b.oha
def save(port,route,c,seconds,ka):
	global serial
	r=original(port,route,c,seconds,ka)
	(out/f'oha-{serial:03}.json').write_text(json.dumps({'port':port,'route':route,'concurrency':c,'seconds':seconds,'keepalive':ka,'exit':0,'result':r})+'\n');serial+=1
	return r
b.oha=save
try:
	for i,name in enumerate(['off','requests']):
		b.PORTS[name]=18104+i;logs[name]=(out/f'{name}.log').open('wb')
		procs[name]=subprocess.Popen(['taskset','-c',b.SERVER_CPUS,str(m.STOCK),'serve','--bind',f'127.0.0.1:{b.PORTS[name]}','--log',name,str(m.OLD/'b/site.rn')],stderr=logs[name],stdout=subprocess.DEVNULL,stdin=subprocess.DEVNULL)
	import time
	time.sleep(1)
	for p in procs.values():assert p.poll() is None
	for name in procs:b.wire_reuse(b.PORTS[name])
	for rep in range(3):
		for name in (['off','requests'] if rep%2==0 else ['requests','off']):
			row={'case':'load','rep':rep,'impl':name,'route':'/hello/world','concurrency':32,'keepalive':True,**b.measure(name,procs[name],'/hello/world',32,True,rep==0)}
			rows.append(row);print(json.dumps(row),flush=True)
finally:
	for p in procs.values():p.terminate();assert p.wait(timeout=10)==0
	for l in logs.values():l.close()
	(out/'results.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
assert len(rows)==6
# Server request logs can be enormous: retain exact counts + hash and failure/summary
# records instead of storing millions of repeated request rows in git.
import hashlib
for name in logs:
	path=out/f'{name}.log';sha=hashlib.sha256();counts={};keep=[]
	with path.open('rb') as stream:
		for line in stream:
			sha.update(line);r=json.loads(line);event=r['event'];counts[event]=counts.get(event,0)+1
			if event!='request':keep.append(r)
	(out/f'{name}-log-summary.json').write_text(json.dumps({'sha256':sha.hexdigest(),'bytes':path.stat().st_size,'events':counts,'other_records':keep},indent=2)+'\n')
	path.unlink()
