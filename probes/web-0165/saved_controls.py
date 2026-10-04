"""Mutations of complete retained artifacts must be refused, including both row + artifact edits."""
import json,pathlib,shutil,subprocess,sys,tempfile
HERE=pathlib.Path(__file__).resolve().parent;source=pathlib.Path(sys.argv[1]);validate=HERE/'validate_saved.py'
def run(path):return subprocess.run([sys.executable,validate,path],capture_output=True,text=True)
assert run(source).returncode==0
cases=[]
def alter_json(path,name,change):
	p=path/name;r=json.loads(p.read_text());change(r);p.write_text(json.dumps(r))
def alter_rows(path,change):
	p=path/'results.jsonl';rows=[json.loads(l) for l in p.read_text().splitlines()];change(rows);p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
cases.append(('missing artifact',lambda p:(p/'oha-001.json').unlink()))
cases.append(('extra artifact',lambda p:shutil.copy(p/'oha-001.json',p/'oha-999.json')))
cases.append(('missing row',lambda p:alter_rows(p,lambda r:r.pop())))
cases.append(('duplicate row',lambda p:alter_rows(p,lambda r:r.append(r[-1]))))
cases.append(('wrong exit',lambda p:alter_json(p,'oha-001.json',lambda r:r.update(exit=1))))
cases.append(('truncated stdout',lambda p:alter_json(p,'oha-001.json',lambda r:r.update(stdout='{'))))
cases.append(('wrong port',lambda p:alter_json(p,'oha-001.json',lambda r:r.update(port=1))))
cases.append(('wrong duration',lambda p:alter_json(p,'oha-001.json',lambda r:r.update(seconds=9))))
cases.append(('latency detached from row',lambda p:alter_rows(p,lambda r:r[-1].update(p50_ms=r[-1]['p50_ms']*2))))
cases.append(('missing occupancy',lambda p:alter_rows(p,lambda r:r[3].pop('connections'))))
cases.append(('unexpected repetition',lambda p:alter_rows(p,lambda r:r[-1].update(rep=3))))
cases.append(('warmup detached from condition',lambda p:alter_json(p,'oha-000.json',lambda r:r.update(port=1))))
cases.append(('command detached from artifact',lambda p:alter_json(p,'oha-001.json',lambda r:r['argv'].append('--invalid'))))
for name,change in cases:
	with tempfile.TemporaryDirectory() as temp:
		path=pathlib.Path(temp)/'copy';shutil.copytree(source,path);change(path)
		assert run(path).returncode!=0,name
		print(name,'REFUSED')
print(len(cases),'saved-evidence corruptions refused; unmodified PASS')
