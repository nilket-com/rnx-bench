"""Same stock binary: manual helpers / built-in web helpers, reusing frozen 0162 bytes and gates.
Three interleaved repetitions, 3s warmup / 10s measured. Retain every exit and complete JSON.
"""
import hashlib, importlib.util, json, os, pathlib, statistics, subprocess, sys, time
HERE=pathlib.Path(__file__).resolve().parent
OLD=HERE.parent/'web-0162'
spec=importlib.util.spec_from_file_location('web0162',OLD/'bench.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
STOCK=HERE/'target/stock'
CONDITIONS=[('/',1,True),('/',32,True),('/hello/world',1,True),('/hello/world',32,True),('/hello/world',1,False)]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def start(name,out,logs):
	port=b.PORTS[name]
	cmd=[str(STOCK),'serve','--bind',f'127.0.0.1:{port}','--workers','2','--log','off',str(HERE/('before.rn' if name=='A' else 'after.rn'))]
	logs[name]=open(out/f'{name}-server.log','w+')
	began=time.monotonic()
	p=subprocess.Popen(['taskset','-c',b.SERVER_CPUS,*cmd],env={**os.environ,'WORKERS':'2'},stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=logs[name])
	try:
		deadline=began+15
		while True:
			if p.poll() is not None:raise RuntimeError((name,'startup exit',p.returncode))
			try:
				if any(json.loads(l).get('event')=='ready' for l in (out/f'{name}-server.log').read_text().splitlines() if l.startswith('{')):break
			except OSError:pass
			if time.monotonic()>=deadline:raise RuntimeError((name,'no ready'))
			time.sleep(.001)
		ready_ms=(time.monotonic()-began)*1000
		check=subprocess.run([sys.executable,str(OLD/'check.py'),f'http://127.0.0.1:{port}'],capture_output=True,text=True)
		(out/f'{name}-fixtures.txt').write_text(check.stdout+check.stderr)
		assert check.returncode==0,(name,check.stdout,check.stderr)
		b.wire_reuse(port);print(name,'26 fixtures + 3-response reuse PASS',flush=True)
		return p,ready_ms,cmd
	except BaseException:p.terminate();p.wait(timeout=15);raise

def main(out):
	out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=False)
	(out/'conditions.json').write_text(json.dumps({'binary':str(STOCK),'binary_sha256':sha(STOCK),'sources':{n:sha(HERE/n) for n in ['before.rn','after.rn']},'server_cpus':b.SERVER_CPUS,'load_cpus':b.LOAD_CPUS,'conditions':CONDITIONS,'repetitions':3,'warmup_seconds':3,'measured_seconds':10},indent=2)+'\n')
	rows=[];procs={};logs={};serial=0
	def saved_oha(port,route,c,seconds,ka):
		nonlocal serial
		cmd=['taskset','-c',b.LOAD_CPUS,'oha','--no-tui','--output-format','json','-z',f'{seconds}s','-c',str(c),'-w','--http-version','1.1']
		if not ka:cmd+=['--disable-keepalive']
		cmd+=[f'http://127.0.0.1:{port}{route}']
		p=subprocess.run(cmd,capture_output=True,text=True,timeout=seconds+20)
		artifact={'port':port,'route':route,'concurrency':c,'seconds':seconds,'keepalive':ka,'argv':cmd,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
		try:artifact['result']=json.loads(p.stdout)
		except json.JSONDecodeError:artifact['result']=None
		(out/f'oha-{serial:03}.json').write_text(json.dumps(artifact)+'\n');serial+=1
		if p.returncode or artifact['result'] is None:raise b.Refused(f'oha failed: {p.returncode}')
		return artifact['result']
	b.oha=saved_oha
	try:
		for name in 'AB':
			p,ms,cmd=start(name,out,logs);procs[name]=p
			rows.append({'case':'ready','impl':name,'ready_ms':ms,'rss_kib':b.tree_rss(p.pid),'argv':cmd})
		for rep in range(3):
			for route,c,ka in CONDITIONS:
				for name in ('AB' if rep%2==0 else 'BA'):
					r=b.measure(name,procs[name],route,c,ka,rep==0)
					row={'case':'load','rep':rep,'impl':name,'route':route,'concurrency':c,'keepalive':ka,**r};rows.append(row);print(json.dumps(row),flush=True)
	finally:
		for p in procs.values():p.terminate();p.wait(timeout=15)
		for log in logs.values():log.close()
		(out/'results.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
	assert len([r for r in rows if r['case']=='load'])==30
	summary=[]
	for route,c,ka in CONDITIONS:
		for name in 'AB':
			r=[r for r in rows if r['case']=='load' and (r['impl'],r['route'],r['concurrency'],r['keepalive'])==(name,route,c,ka)]
			summary.append({'impl':name,'route':route,'c':c,'ka':ka,'rps':statistics.median(x['rps'] for x in r),'rps_range':[min(x['rps'] for x in r),max(x['rps'] for x in r)],'p50_ms':statistics.median(x['p50_ms'] for x in r),'p99_ms':statistics.median(x['p99_ms'] for x in r)})
	(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
	gate=[{'route':route,'c':c,'ka':ka,'new_over_old':summary[2*i+1]['rps']/summary[2*i]['rps']} for i,(route,c,ka) in enumerate(CONDITIONS)]
	(out/'throughput-gate.json').write_text(json.dumps(gate,indent=2)+'\n')
	print(json.dumps(summary,indent=2),flush=True)
	assert all(r['new_over_old'] >= .95 for r in gate),gate
if __name__=='__main__':
	if sys.argv[1:]==['--controls']:sys.exit(0 if b.controls() else 1)
	main(sys.argv[1])
