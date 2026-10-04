"""Separate readiness, excluding fixtures; C waits for two loaded workers, not master bind."""
import importlib.util,json,os,pathlib,socket,subprocess,sys,tempfile,time,statistics
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('host',HERE/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
out=pathlib.Path(sys.argv[1]);rows=[]
for rep in range(10):
	for name in ('ABC' if rep%2==0 else 'CBA'):
		port={'A':18701,'B':18702,'C':18703}[name]
		if name=='A':cmd=[str(m.OLD/'a/target/release/web0162-a'),f'127.0.0.1:{port}']
		elif name=='B':cmd=[str(m.STOCK),'serve','--bind',f'127.0.0.1:{port}','--log','off',str(m.OLD/'b/site.rn')]
		else:cmd=[str(m.OLD/'c/.venv/bin/gunicorn'),'-k','gthread','-w','2','--threads','4','--keep-alive','5','-b',f'127.0.0.1:{port}','--chdir',str(m.OLD/'c'),'--config',str(HERE/'gunicorn_ready.py'),'app:app']
		with tempfile.TemporaryDirectory() as temp:
			path=pathlib.Path(temp)/'log';writer=path.open('wb');begin=time.perf_counter_ns()
			p=subprocess.Popen(['taskset','-c',m.b.SERVER_CPUS,*cmd],env={**os.environ,'WORKERS':'2'},stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=writer)
			try:
				deadline=time.monotonic()+15
				while True:
					assert p.poll() is None,(name,path.read_text())
					data=path.read_text();events=[json.loads(l) for l in data.splitlines() if l.startswith('{')]
					ready=False
					if name=='B':ready=any(e.get('event')=='ready' for e in events)
					elif name=='C':ready=len({e['pid'] for e in events if e.get('event')=='worker_ready'})==2
					else:
						try:
							with socket.create_connection(('127.0.0.1',port),timeout=.01):ready=True
						except OSError:pass
					if ready:break
					assert time.monotonic()<deadline
					time.sleep(.001)
				row={'impl':name,'rep':rep,'ms':(time.perf_counter_ns()-begin)/1e6,'definition':{'A':'listener accepts; no worker initialization after bind','B':'ready after all stock slots','C':'two post_worker_init callbacks, app loaded'}[name]};rows.append(row);print(json.dumps(row),flush=True)
				# Verify the ready process answers, but outside the measured interval.
				m.b.wire_reuse(port)
			finally:p.terminate();p.wait(timeout=15);writer.close()
out.write_text(json.dumps({'rows':rows,'medians_ms':{n:statistics.median(r['ms'] for r in rows if r['impl']==n) for n in 'ABC'}},indent=2)+'\n')
