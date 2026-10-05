"""Fixed protocol; native timing, independently validated results, all raw rows retained."""
import hashlib,json,os,pathlib,random,statistics,subprocess,time
P=pathlib.Path(__file__).resolve().parent; ROOT=P.parents[1]; O=ROOT/'results/lua-rust-0001';T=P/'target';T.mkdir(exist_ok=True)
os.environ['OMNILUA_VERSION']='5.4'; original=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,{4})
BIN={'piccolo':'/tmp/lua-rust-0001/piccolo/target/release/examples/interpreter','omnilua':'/tmp/lua-rust-0001/install/bin/omnilua','lua54':os.path.expanduser('~/.local/bin/lua54'),'luajit':os.path.expanduser('~/.local/bin/luajit'),'rnx-run':str(ROOT/'probes/fmt-0167/target/stock'),'rnx-eval':str(ROOT/'probes/fmt-0167/target/stock'),'python':'/usr/bin/python3'}
def checked(cmd):
 r=subprocess.run(cmd,capture_output=True,timeout=60);assert r.returncode==0 and not r.stderr,(cmd,r.returncode,r.stderr);return r.stdout
subprocess.run(['rustc','-O',str(P/'clock.rs'),'-o',str(T/'clock')],check=True)
(T/'cached.rs').write_text('fn main() { println!("42"); }\n');subprocess.run(['rustc',str(T/'cached.rs'),'-o',str(T/'cached')],check=True)
def clock(cmd):
 r=checked([str(T/'clock'),'1',str(len(cmd)),*cmd]); lines=r.decode().splitlines();assert len(lines)==4 and lines[1]=='0' and lines[3]=='',r;return int(lines[0]),bytes.fromhex(lines[2])
def command(subject,work):
 exe=BIN[subject]
 if subject=='rnx-run':return [exe,'run','--budget','1000000000',str(P/(work+'.rn'))]
 if subject=='rnx-eval':
  s=(P/(work+'.rn')).read_text();at=s.index('pub fn main(_args)');prefix=s[:at];body=s[at+len('pub fn main(_args) '):].strip();code=body[0]+prefix+body[1:];return [exe,'eval',code]
 return [exe,str(P/(work+('.py' if subject=='python' else '.lua')))]
# Contemporary independent references, then preflight native gate.
pre={}
for name,cmd,expected in [('true',['/bin/true'],b''),('cached',[str(T/'cached')],b'42\n')]:
 hf=O/('hyperfine-'+name+'.json');subprocess.run(['taskset','-c','4','hyperfine','-N','--warmup','5','--runs','50','--export-json',str(hf),*cmd],check=True,stdout=subprocess.DEVNULL)
 ref=statistics.median(json.loads(hf.read_text())['results'][0]['times'])*1000
 ns=[]
 for i in range(55):
  n,out=clock(cmd);assert out==expected
  if i>=5:ns.append(n)
 med=statistics.median(ns)/1e6;pre[name]=dict(reference_ms=ref,ns=ns,median_ms=med,passed=abs(med-ref)<=.15)
(O/'preflight.json').write_text(json.dumps(pre,indent=2)+'\n');assert all(x['passed'] for x in pre.values()),'STOP clock preflight'
expected={w:checked([BIN['python'],str(P/(w+'.py'))]) for w in ['empty','answer','numeric','strings','fib']}
checks=[];cases=[]
for subject in BIN:
 for work,out in expected.items():
  cmd=command(subject,work);got=checked(cmd);assert got==out,(subject,work,got,out);cases.append((subject,work,cmd,out));checks.append(dict(subject=subject,work=work,output=got.decode(),command=cmd))
(O/'validation.json').write_text(json.dumps(checks,indent=2)+'\n')
libs={}
for s in ['piccolo','omnilua','lua54','luajit']:libs[s]=checked([BIN[s],str(P/'libraries.lua')]).decode()
(O/'libraries.json').write_text(json.dumps(libs,indent=2)+'\n')
conditions={'original_affinity':original,'pinned':[4],'omnilua_env':{'OMNILUA_VERSION':'5.4'},'machine':checked(['uname','-a']).decode(),'cpu':pathlib.Path('/proc/cpuinfo').read_text(),'rustc':checked(['rustc','-vV']).decode(),'binaries':{k:dict(path=v,bytes=pathlib.Path(v).stat().st_size,sha256=hashlib.sha256(pathlib.Path(v).read_bytes()).hexdigest()) for k,v in BIN.items()},'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in P.iterdir() if p.is_file()},'commands':checks}
(O/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
# Separate RSS: no /usr/bin/time wrapper in primary timings.
rss=[]
for subject,work,cmd,out in cases:
 f=T/'rss.txt';r=subprocess.run(['/usr/bin/time','-f','%M','-o',str(f),*cmd],capture_output=True,timeout=60);assert r.returncode==0 and r.stdout==out and not r.stderr;rss.append(dict(subject=subject,work=work,maxrss_kib=int(f.read_text())))
(O/'rss.json').write_text(json.dumps(rss,indent=2)+'\n')
raw=O/'samples.jsonl';assert not raw.exists(),'refuse overwrite'
with raw.open('w') as f:
 for subject,work,cmd,out in cases:
  for _ in range(5 if work in ['empty','answer'] else 2):assert clock(cmd)[1]==out
 for repeat in range(3):
  rows=[(c,i) for c in cases for i in range(30 if c[1] in ['empty','answer'] else 5)];random.Random(5100+repeat).shuffle(rows)
  for (subject,work,cmd,out),i in rows:
   n,got=clock(cmd);assert got==out;f.write(json.dumps(dict(subject=subject,work=work,repeat=repeat,sample=i,ns=n,affinity=[4]))+'\n');f.flush()
  print('round',repeat,'complete',flush=True)
 os.sched_setaffinity(0,original)
 for subject in BIN:
  cmd=command(subject,'answer');out=expected['answer']
  for _ in range(5):assert clock(cmd)[1]==out
  for i in range(30):
   n,got=clock(cmd);assert got==out;f.write(json.dumps(dict(subject=subject,work='answer-unpinned',repeat=0,sample=i,ns=n,affinity=original))+'\n');f.flush()
print('complete',flush=True)
