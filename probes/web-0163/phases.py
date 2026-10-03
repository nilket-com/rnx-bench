"""0163 phase sample and lifecycle control, reusing the 0162 drivers with a slot host.
python3 probes/web-0163/phases.py
python3 probes/web-0163/phases.py --control
"""
import argparse,importlib.util,json,pathlib,subprocess,sys,tempfile
HERE=pathlib.Path(__file__).resolve().parent;OLD=HERE.parent/'web-0162'
spec=importlib.util.spec_from_file_location('phases0162',OLD/'phases.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
parser=argparse.ArgumentParser()
parser.add_argument('--control',action='store_true')
parser.add_argument('--baseline',action='store_true')
parser.add_argument('--out',type=pathlib.Path)
args=parser.parse_args()
with tempfile.TemporaryFile(mode='w+') as log:
	control=args.control;port=18032
	proc=subprocess.Popen(['taskset','-c','2,4',str(OLD/'b/target/release/web0162-b' if args.baseline else HERE/'b/target/release/web0163-b'),str(OLD/'b'/('control.rn' if control else 'site.rn')),f'127.0.0.1:{port}'],env={'WORKERS':'1',**({} if control else {'PHASES':'1'})},stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=log)
	try:
		if not control:m.drive(port)
		else:
			import http.client,time
			time.sleep(1)
			for path,want in [('/ok',200),('/panic',500),('/ok',200),('/loop',500),('/ok',200),('/refuse',500),('/ok',200)]:
				conn=http.client.HTTPConnection('127.0.0.1',port,timeout=10);conn.request('GET',path);r=conn.getresponse();body=r.read();assert r.status==want,(path,r.status,body);conn.close();print(path,r.status)
	finally:proc.terminate();proc.wait(timeout=15)
	log.seek(0);lines=log.read().splitlines()
if args.out:args.out.write_text('\n'.join(lines)+'\n')
if not control:
	for route,line in m.summarize(lines).items():print(route,json.dumps(line))
else:
	events=[json.loads(l) for l in lines if l.startswith('{"event":"handler_error"')]
	assert len(events)==3
	assert [e['reason'].split(':')[0] for e in events]==['vm','vm','status']
	assert [e['close'] for e in events]==['vm','vm','closed']
	print('Slot lifecycle host control PASS',json.dumps(events))
