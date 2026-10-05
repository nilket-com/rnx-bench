"""Untimed capabilities, versions and resource policy; no claims of full conformance."""
import hashlib,json,pathlib,subprocess
P=pathlib.Path(__file__).resolve().parent;O=P.parents[1]/'results/lua-rust-0001'
bins=json.loads((O/'conditions.json').read_text())['binaries'];rows={}
for name,info in bins.items():
 cmd=[info['path'],*(['--version'] if name in ['piccolo','rnx-run','rnx-eval','python'] else ['-v'])]
 r=subprocess.run(cmd,capture_output=True);rows[name]=dict(command=cmd,status=r.returncode,stdout=r.stdout.decode(),stderr=r.stderr.decode())
policy={}
for key in ['scaling_governor','scaling_driver','cpuinfo_min_freq','cpuinfo_max_freq']:
 p=pathlib.Path('/sys/devices/system/cpu/cpu4/cpufreq')/key;policy[key]=p.read_text().strip() if p.exists() else None
(O/'audit.json').write_text(json.dumps(dict(versions=rows,frequency_policy=policy,locks={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (P/'locks').iterdir()}),indent=2)+'\n')
# JSON functionality as shipped for Python and rnx; no new Lua modules installed.
(P/'json_roundtrip.py').write_text('import json\nprint(json.loads(json.dumps({"answer":42}))["answer"])\n')
(P/'json.rn').write_text('pub fn main(_args) { let text=json::stringify(#{answer:42})?; let value=json::parse(text)?; println!("{}",value.answer); }\n')
json_rows=[]
for name,cmd in [('python',[bins['python']['path'],str(P/'json_roundtrip.py')]),('rnx-run',[bins['rnx-run']['path'],'run',str(P/'json.rn')])]:
 r=subprocess.run(cmd,capture_output=True);assert r.returncode==0 and r.stdout==b'42\n' and not r.stderr;json_rows.append(dict(subject=name,command=cmd,stdout=r.stdout.decode(),status=r.returncode))
(O/'json-capabilities.json').write_text(json.dumps(json_rows,indent=2)+'\n')
