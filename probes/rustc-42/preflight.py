"""Fail closed before the native-clock deciding run; references reviewed in advance."""
import hashlib,json,os,pathlib,statistics,subprocess,sys
P=pathlib.Path(__file__).resolve().parent
O=pathlib.Path(sys.argv[1]);assert not O.exists()
os.sched_setaffinity(0,{4})
helper=P/'target/clock'
cases={'true':(['/bin/true'],.24,b''),'cached':([str(P/'target/warm-print-default')],.353,b'42\n')}
rows={}
for name,(argv,reference,expected) in cases.items():
	samples=[]
	for i in range(55):
		r=subprocess.run([str(helper),'1',str(len(argv)),*argv],capture_output=True,text=True,timeout=10);assert r.returncode==0,r
		lines=r.stdout.splitlines();assert len(lines)==4 and lines[1]=='0' and bytes.fromhex(lines[2])==expected and lines[3]=='',lines
		if i>=5:samples.append(int(lines[0]))
	median=statistics.median(samples)/1e6
	rows[name]={'ns':samples,'median_ms':median,'reference_ms':reference,'allowed_delta_ms':.15,'passed':abs(median-reference)<=.15}
j={'helper_sha256':hashlib.sha256(helper.read_bytes()).hexdigest(),'affinity':[4],'rows':rows,'passed':all(r['passed'] for r in rows.values())}
O.write_text(json.dumps(j,indent=2)+'\n')
assert j['passed'],'STOP: native clock disagrees with independent hyperfine references'
print('native clock preflight PASS')
