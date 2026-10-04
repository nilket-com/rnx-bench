"""Replay the reviewer's scratch upstream binary under explicit OS limits.
Usage: upstream.py BINARY OUTPUT_DIR. Build recipe and source are retained beside it.
"""
import hashlib,json,pathlib,resource,subprocess,sys
binary=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=False)
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(1000000000,1000000000))
 resource.setrlimit(resource.RLIMIT_CPU,(2,2))
rows=[]
for name,source,args in [
 ('macro','pub fn main() { println!("x",\n',[]),
 ('macro-strict','pub fn main() { println!("x",\n',['fmt.error-recovery=false']),
 ('call','pub fn main() { foo(1,\n',['fmt.error-recovery=false']),
 ('template','pub fn main(){let x=`a { b`;}',['fmt.error-recovery=false']),
 ('tabs','fn a(){let x=1;}',['fmt.indent=tab']),
]:
 p=out/(name+'.rn');p.write_text(source)
 r=subprocess.run([str(binary),str(p),*args],capture_output=True,text=True,preexec_fn=limits,timeout=5)
 rows.append(dict(name=name,source=source,args=args,exit=r.returncode,stdout=r.stdout,stderr=r.stderr))
assert rows[0]['exit']==rows[1]['exit']==1
assert rows[2]['exit']==0 and 'foo(1)' in rows[2]['stdout']
assert rows[3]['exit']==0 and '`a { b`' in rows[3]['stdout']
assert rows[4]['exit']==0 and '\n\tlet' in rows[4]['stdout']
(out/'results.json').write_text(json.dumps(dict(upstream_commit='bb8e69372353c50e271c9f115bc771c77aa6b83e',binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),address_space_bytes=1000000000,cpu_seconds=2,wall_seconds=5,cases=rows),indent=2)+'\n')
print('upstream allocation refusal, remaining silent completion, template fix and tabs confirmed')
