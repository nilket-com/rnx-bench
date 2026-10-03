"""Reapply the load gates to every retained measured oha result and check run completeness."""
import importlib.util,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('bench0162',HERE.parent/'web-0162/bench.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def check(out):
	rows=[json.loads(l) for l in (out/'results.jsonl').read_text().splitlines()]
	ready=[r for r in rows if r['case']=='ready'];load=[r for r in rows if r['case']=='load']
	assert len(ready)==2 and {r['impl'] for r in ready}=={'B','S'}
	expected={(rep,name,route,c) for rep in range(3) for name in ['B','S'] for route in ['/','/hello/world'] for c in [1,32]}
	assert len(load)==24 and {(r['rep'],r['impl'],r['route'],r['concurrency']) for r in load}==expected
	order=[(rep,name,route,c) for rep in range(3) for route,c in [('/',1),('/',32),('/hello/world',1),('/hello/world',32)] for name in (['B','S'] if rep%2==0 else ['S','B'])]
	assert [(r['rep'],r['impl'],r['route'],r['concurrency']) for r in load]==order

	files=sorted(out.glob('oha-*.json'));assert len(files)==48
	measured=[]
	for index,p in enumerate(files):
		o=json.loads(p.read_text());assert o['seconds']==(3 if index%2==0 else 10) and o['keepalive'] is True
		if o['seconds']==10:measured.append(o)
		else:b.validate(o['result'],o['concurrency'],False,None) # warm-up has no connection sample
	assert len(measured)==len(load)
	for row,o in zip(load,measured):
		assert o['port']==({'B':18102,'S':18104}[row['impl']])
		assert (o['route'],o['concurrency'])==(row['route'],row['concurrency'])
		accepted=b.validate(o['result'],o['concurrency'],True,row['connections'])
		assert all(row[k]==v for k,v in accepted.items()),'retained JSON differs from its reported row'
	print('PASS: 24 complete matched load rows, full oha gates replayed; 24 warm-ups validated')
if __name__=='__main__':check(pathlib.Path(sys.argv[1]))
