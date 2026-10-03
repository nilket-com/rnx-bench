"""0163: matched B/B-prime run. Reuses the reviewed 0162 fixtures and fail-closed load gates.
Build both hosts first; runs 3 interleaved repetitions at c=1/32 for / and /hello/world.
All servers use CPUs 2,4; oha CPUs 8,10,12,14; warm 3s, measured 10s.
python3 probes/web-0163/run.py NEW_OUTPUT_DIRECTORY
"""
import importlib.util,json,os,pathlib,statistics,subprocess,sys,tempfile,time
HERE=pathlib.Path(__file__).resolve().parent
OLD=HERE.parent/'web-0162'
spec=importlib.util.spec_from_file_location('web0162',OLD/'bench.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
b.PORTS['S']=18104
B=OLD/'b/target/release/web0162-b'
S=HERE/'b/target/release/web0163-b'

def start(name, log):
	proc=subprocess.Popen(['taskset','-c',b.SERVER_CPUS,str(B if name=='B' else S),str(OLD/'b/site.rn'),f'127.0.0.1:{b.PORTS[name]}'],env={'WORKERS':'2'},stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=log)
	began=time.monotonic()
	try:
		deadline=began+15
		while True:
			if proc.poll() is not None:raise RuntimeError(f'{name} exited during startup')
			try:b.wire_reuse(b.PORTS[name]);break
			except (OSError,b.Refused):
				if time.monotonic()>=deadline:raise
				time.sleep(.01)
		ready_ms=(time.monotonic()-began)*1000
		r=subprocess.run([sys.executable,str(OLD/'check.py'),f'http://127.0.0.1:{b.PORTS[name]}'],capture_output=True,text=True,check=True)
		print(name,r.stdout.strip(), 'wire reuse PASS',flush=True)
		return proc,ready_ms
	except BaseException:proc.terminate();proc.wait(timeout=15);raise

def main(out):
	out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=False)
	rows=[];procs={};logs={}
	# Retain the complete warm-up and measured oha JSON, not only summary fields.
	original_oha=b.oha
	serial=0
	def saved_oha(port, route, concurrency, seconds, keepalive):
		nonlocal serial
		result=original_oha(port,route,concurrency,seconds,keepalive)
		(out/f'oha-{serial:03}.json').write_text(json.dumps({'port':port,'route':route,'concurrency':concurrency,'seconds':seconds,'keepalive':keepalive,'result':result})+'\n')
		serial+=1
		return result
	b.oha=saved_oha
	try:
		for name in ['B','S']:
			logs[name]=open(out/f'{name}-server.log','w+')
			procs[name],ms=start(name,logs[name])
			row={'case':'ready','impl':name,'probe_ready_ms':ms,'rss_kib':b.tree_rss(procs[name].pid)};rows.append(row);print(json.dumps(row),flush=True)
		for rep in range(3):
			for route,c in [('/',1),('/',32),('/hello/world',1),('/hello/world',32)]:
				for name in (['B','S'] if rep%2==0 else ['S','B']):
					r=b.measure(name,procs[name],route,c,True,rep==0)
					row={'case':'load','rep':rep,'impl':name,'route':route,'concurrency':c,'keepalive':True,**r};rows.append(row);print(json.dumps(row),flush=True)
	finally:
		for p in procs.values():p.terminate();p.wait(timeout=15)
		for log in logs.values():log.close()
		(out/'results.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
	for route,c in [('/',1),('/',32),('/hello/world',1),('/hello/world',32)]:
		for name in ['B','S']:
			r=[r for r in rows if r['case']=='load' and (r['impl'],r['route'],r['concurrency'])==(name,route,c)]
			print(name,route,c,'rps',statistics.median(x['rps'] for x in r),'range',[min(x['rps'] for x in r),max(x['rps'] for x in r)],'p50_ms',statistics.median(x['p50_ms'] for x in r),'p99_ms',statistics.median(x['p99_ms'] for x in r),flush=True)

if __name__=='__main__':main(sys.argv[1])
