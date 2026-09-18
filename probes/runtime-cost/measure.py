"""Interleaved everyday, verify and direct launches; no concurrent build workload."""
from pathlib import Path
import os,sys,json,subprocess as sp,time,random,statistics,tempfile,importlib.util,hashlib,shutil,socket,struct
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/runtime-cost-0064';state=json.loads((W/'setup.json').read_text());E=state['env'];T=state['tool'];cells=state['cells'];assert len(cells)==4
assert not (O/'launch-samples.jsonl').exists(), 'remove previous timing journal before rerunning'
cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu});rng=random.Random(640506)
spec=importlib.util.spec_from_file_location('terminal',B/'probes/project-interactive/common.py');term=importlib.util.module_from_spec(spec);spec.loader.exec_module(term)
def save(n,v):(O/n).write_text(json.dumps(v,indent=2)+'\n')
def command(c,mode,kind):
 a=c['artifact'];m=c['manifest'];flags=['--verify'] if kind=='verify' else []
 if mode=='run':return [a,'run',str(Path(m).parent/'entry.rn')] if kind=='direct' else [T,'run','--manifest',m,*flags]
 if mode=='eval':return [a,'--color=never','eval','polars::lit(1).is_ok()'] if kind=='direct' else [T,'eval','--manifest',m,*flags,'--color=never','--','polars::lit(1).is_ok()']
 return [a,'--no-splash','--color=never','repl'] if kind=='direct' else [T,'session','--manifest',m,*flags,'--no-splash','--color=never']
rows=[]
for repeat in range(2):
 jobs=[(c,mode,kind,i) for c in cells for mode in ['run','eval','session'] for kind in ['default','verify','direct'] for i in range(20)];rng.shuffle(jobs)
 for c,mode,kind,i in jobs:
  with tempfile.TemporaryDirectory(prefix='rnx-runtime-cost-') as directory:
   cwd=Path(directory);env=dict(E,RNX_CONFIG=str(cwd/'absent'),RNX_HISTORY=str(cwd/'history'));args=command(c,mode,kind);start=time.perf_counter_ns()
   if mode=='session':
    t=term.Terminal(args,cwd,env)
    try:
     out=t.read();ms=(time.perf_counter_ns()-start)/1e6;assert out=='\r[1] > \r',repr(out);os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
    finally:t.close()
   else:
    p=sp.run(args,env=env,cwd=cwd,capture_output=True,text=True,timeout=30);ms=(time.perf_counter_ns()-start)/1e6;assert p.returncode==0 and p.stdout=='true\n' and not p.stderr,(args,p.stdout,p.stderr)
   rows.append(dict(repeat=repeat,origin=c['origin'],natives=c['natives'],mode=mode,kind=kind,sample=i,ms=ms))
  with (O/'launch-samples.jsonl').open('a') as f:f.write(json.dumps(rows[-1])+'\n')
 summary=[]
 for c in cells:
  for mode in ['run','eval','session']:
   med={kind:statistics.median(r['ms'] for r in rows if r['repeat']==repeat and r['origin']==c['origin'] and r['natives']==c['natives'] and r['mode']==mode and r['kind']==kind) for kind in ['default','verify','direct']}
   summary.append(dict(repeat=repeat,origin=c['origin'],natives=c['natives'],mode=mode,**med,over_direct=med['default']-med['direct']))
 save(f'launch-summary-{repeat}.json',summary);print('PASS launch repeat',repeat,len(rows),flush=True)
# Ready attachment includes full hash; forbid all compile invocations with positive controls.
traps=W/'traps';traps.mkdir();traplog=W/'compile-trap.log'
for name in ['cargo','rustc']:
 real=shutil.which(name);p=traps/name;p.write_text('#!/usr/bin/python3\nimport os,sys\na=sys.argv[1:]\nbad=("build" in a or "rustc" in a) if '+repr(name)+'=="cargo" else ("--crate-name" in a and not any(v.startswith("--print") for v in a))\nif bad:\n open('+repr(str(traplog))+',"a").write(repr(a)+"\\n")\n raise SystemExit(91)\nos.execv('+repr(real)+',['+repr(real)+',*a])\n');p.chmod(0o755)
trapped=dict(E,PATH=str(traps)+':'+E['PATH'])
for args in [[str(traps/'cargo'),'build'],[str(traps/'rustc'),'--crate-name','positive']]:assert sp.run(args,env=trapped,capture_output=True).returncode==91
traplog.unlink();attachments=[]
for repeat in range(2):
 jobs=[(c,i) for c in cells for i in range(5)];rng.shuffle(jobs)
 for c,i in jobs:
  a=Path(c['artifact']);ready=a.parent.parent/'ready.json';before=(ready.read_bytes(),a.stat().st_ino,a.stat().st_mtime_ns)
  start=time.perf_counter_ns();p=sp.run([T,'build','--offline','--manifest',c['manifest']],env=trapped,cwd=W,capture_output=True,text=True,timeout=60);ms=(time.perf_counter_ns()-start)/1e6
  assert p.returncode==0 and 'attached shared' in p.stderr+p.stdout,(p.stdout,p.stderr);assert not traplog.exists();assert before==(ready.read_bytes(),a.stat().st_ino,a.stat().st_mtime_ns)
  attachments.append(dict(repeat=repeat,origin=c['origin'],natives=c['natives'],sample=i,ms=ms));save('attachments.json',attachments)
# Private describe protocol: spawn to validated notice, then decline and wait.
def frame(k,f):
 b=bytes([1,k])+b''.join(bytes([n])+struct.pack('!I',len(v.encode()))+v.encode() for n,v in sorted(f.items()));return struct.pack('!I',len(b))+b
def exact(s,n):
 b=b''
 while len(b)<n:
  v=s.recv(n-len(b));assert v;b+=v
 return b
def recv(s):
 n=struct.unpack('!I',exact(s,4))[0];b=exact(s,n);i=2;f={}
 while i<len(b):
  tag=b[i];n=struct.unpack('!I',b[i+1:i+5])[0];i+=5;f[tag]=b[i:i+n].decode();i+=n
 return b[1],f
describes=[]
for repeat in range(2):
 jobs=[(c,i) for c in cells for i in range(20)];rng.shuffle(jobs)
 for c,i in jobs:
  a,b=socket.socketpair();a.settimeout(10);env=dict(E,RNX_INTERNAL_DEP_FD=str(b.fileno()))
  if c['origin']=='checkout':env['RNX_DEP_RUNTIME']=state['checkout']
  start=time.perf_counter_ns();p=sp.Popen([T],env=env,pass_fds=(b.fileno(),),stdin=sp.DEVNULL,stdout=sp.PIPE,stderr=sp.PIPE);b.close();a.sendall(frame(1,{1:'polars' if c['natives']==1 else 'polars\npostgres',2:'',3:c['artifact'],4:'',5:'offline'}));k,d=recv(a);ms=(time.perf_counter_ns()-start)/1e6;assert k==2,d
  assert ('Runtime: installation' if c['origin']=='installed' else 'Runtime: override') in d[2];a.sendall(frame(3,{}));a.shutdown(socket.SHUT_WR);a.close();out,err=p.communicate(timeout=10);assert p.returncode==0 and not out and not err
  describes.append(dict(repeat=repeat,origin=c['origin'],natives=c['natives'],sample=i,ms=ms));save('describe.json',describes)
# File trace checks that normal launch never performs installed discovery validation.
for c in cells:
 if c['origin']!='installed':continue
 trace=O/f"launch-files-{c['natives']}.log";p=sp.run(['strace','-f','-e','trace=%file','-o',str(trace),*command(c,'eval','default')],env=E,cwd=W,capture_output=True,text=True);assert p.returncode==0,(p.stdout,p.stderr)
 raw=trace.read_text();assert 'installation.json' not in raw and 'current.json' not in raw
save('measurement.json',dict(cpu=cpu,launch_samples=len(rows),attachment_samples=len(attachments),describe_samples=len(describes),seed=640506,all_outputs_verified=True,compilation_traps=True,no_installation_metadata_on_launch=True,polars_threads=1))
print('PASS costs complete',len(rows),len(attachments),len(describes),flush=True)
