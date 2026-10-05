"""Deciding uninstrumented whole-process clock; reuse/phase diagnostics separate."""
import hashlib,json,os,pathlib,random,statistics,subprocess
P=pathlib.Path(__file__).resolve().parent;ROOT=P.parents[1];O=ROOT/'results/rune-base-0168';T=P/'target';T.mkdir(exist_ok=True);assert not (O/'samples.jsonl').exists()
original=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,{4})
subprocess.run(['rustc','-O',str(ROOT/'probes/rustc-42/clock.rs'),'-o',str(T/'clock')],check=True)
(T/'cached.rs').write_text('fn main(){println!("42");}\n');subprocess.run(['rustc',str(T/'cached.rs'),'-o',str(T/'cached')],check=True)
def clock(cmd):
 r=subprocess.run([str(T/'clock'),'1',str(len(cmd)),*cmd],capture_output=True,text=True,timeout=30);assert r.returncode==0 and not r.stderr,r.stderr
 lines=r.stdout.splitlines();assert len(lines)==4 and lines[1]=='0';return int(lines[0]),bytes.fromhex(lines[2]).decode(),bytes.fromhex(lines[3]).decode()
pre={}
for label,argv,expect in [('true',['/bin/true'],''),('cached',[str(T/'cached')],'42\n')]:
 f=O/(label+'-hyperfine.json');subprocess.run(['hyperfine','-N','--warmup','5','--runs','50','--export-json',str(f),*argv],check=True,stdout=subprocess.DEVNULL)
 ref=statistics.median(json.loads(f.read_text())['results'][0]['times'])*1000;ns=[]
 for i in range(55):
  n,out,err=clock(argv);assert out==expect and not err
  if i>=5:ns.append(n)
 med=statistics.median(ns)/1e6;pre[label]=dict(ns=ns,reference_ms=ref,median_ms=med,passed=abs(med-ref)<=.15)
(O/'clock-preflight.json').write_text(json.dumps(pre,indent=2)+'\n');assert all(x['passed'] for x in pre.values()),'STOP clock gate'
expected={w:subprocess.run(['/usr/bin/python3',str(ROOT/'probes/lua-rust-0001'/(w+'.py'))],capture_output=True,check=True).stdout.decode() for w in ['empty','answer','numeric','strings','fib']}
CASES=[(mode,None) for mode in ['floor','empty-context','context','runtime']]+[('compile','answer')]+[('run',w) for w in expected]
def argv(base,mode,work):return [str(P/base/'target/release/primary'),mode,*([str(P/'fixtures'/(work+'.rn'))] if work else [])]
checks=[];sources={p.relative_to(P).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in P.rglob('*') if p.is_file() and 'target' not in p.parts and '__pycache__' not in p.parts}
for base in ['old','new']:
 for mode,work in CASES:
  cmd=argv(base,mode,work);r=subprocess.run(cmd,capture_output=True,text=True,timeout=30);expect=expected[work] if mode=='run' else '';assert r.returncode==0 and r.stdout==expect and not r.stderr,(cmd,r.stdout,r.stderr)
  checks.append(dict(base=base,mode=mode,work=work,command=cmd,expected=expect))
(O/'measurement-validation.json').write_text(json.dumps(checks,indent=2)+'\n')
(O/'conditions.json').write_text(json.dumps(dict(original_affinity=original,pin=[4],sources=sources,binaries={base:{kind:dict(path=str(P/base/'target/release'/kind),sha256=hashlib.sha256((P/base/'target/release'/kind).read_bytes()).hexdigest(),size_bytes=(P/base/'target/release'/kind).stat().st_size) for kind in ['primary','counter','allocation']} for base in ['old','new']},rustc=subprocess.check_output(['rustc','-vV'],text=True),machine=subprocess.check_output(['uname','-a'],text=True),commands=checks),indent=2)+'\n')
with (O/'samples.jsonl').open('w') as f:
 for c in checks:
  count=5 if c['work'] not in ['numeric','strings','fib'] else 2
  for _ in range(count):
   _,out,err=clock(c['command']);assert out==c['expected'] and not err
 for rep in range(3):
  tasks=[(c,i) for c in checks for i in range(5 if c['work'] in ['numeric','strings','fib'] else 30)];random.Random(16800+rep).shuffle(tasks)
  for c,i in tasks:
   n,out,err=clock(c['command']);assert out==c['expected'] and not err;f.write(json.dumps(dict(base=c['base'],mode=c['mode'],work=c['work'],repeat=rep,sample=i,ns=n,affinity=[4]))+'\n');f.flush()
  print('round',rep,'complete',flush=True)
 os.sched_setaffinity(0,original)
 for base in ['old','new']:
  cmd=argv(base,'run','answer')
  for _ in range(5):assert clock(cmd)[1:]==('42\n','')
  for i in range(30):
   n,out,err=clock(cmd);assert out=='42\n' and not err;f.write(json.dumps(dict(base=base,mode='unpinned',work='answer',repeat=0,sample=i,ns=n,affinity=original))+'\n');f.flush()
os.sched_setaffinity(0,{4})
diag=[]
for rep in range(3):
 for base in ['old','new']:
  for mode,work in [('phases','answer'),('reuse','answer'),('reuse','numeric'),('reuse','fib'),('registration',None)]:
   r=subprocess.run(argv(base,mode,work),capture_output=True,text=True,timeout=30);assert r.returncode==0
   if mode!='registration':assert r.stdout==expected[work]*(20 if mode=='reuse' else 1)
   diag.append(dict(base=base,mode=mode,work=work,repeat=rep,stdout=r.stdout,stderr=r.stderr))
(O/'inprocess.json').write_text(json.dumps(diag,indent=2)+'\n')
print('complete',flush=True)
