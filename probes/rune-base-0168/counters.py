"""FIFO-bracketed counters, allocation and RSS outside the deciding wall clock."""
import ast,json,os,pathlib,select,signal,subprocess,time,statistics
P=pathlib.Path(__file__).resolve().parent;O=P.parents[1]/'results/rune-base-0168';F=P/'fixtures';os.sched_setaffinity(0,{4})
CASES=[(m,None) for m in ['floor','empty-context','context','runtime','registration']]+[(m,w) for m,w in [('compile','answer'),('run','empty'),('run','answer'),('run','numeric'),('run','strings'),('run','fib'),('phases','answer'),('reuse','answer'),('reuse','numeric'),('reuse','fib')]]
def cmd(base,kind,mode,work):return [str(P/base/'target/release'/kind),mode,*([str(F/(work+'.rn'))] if work else [])]
def counts(text):
 rows=[json.loads(l) for l in text.splitlines() if l.strip()];out={}
 for r in rows:
  k=next((n for n in ['instructions','cycles'] if r['event'] in [n+':u','cpu_core/'+n+'/u']),None);assert k and k not in out,r
  v=float(r['counter-value']);assert v>0 and float(r['pcnt-running'])>=99 and float(r['event-runtime'])>0,r;out[k]=v
 assert len(out)==2;return out
results=[];alloc=[];rss=[]
for base in ['old','new']:
 for mode,work in CASES:
  label=base+'-'+mode+('-'+work if work else '')
  for rep in range(3):
   prefix=O/(label+'-'+str(rep));ctl=prefix.with_suffix('.ctl');ack=prefix.with_suffix('.ack');raw=prefix.with_suffix('.perf.jsonl');os.mkfifo(ctl);os.mkfifo(ack);cf=os.open(ctl,os.O_RDWR|os.O_NONBLOCK);af=os.open(ack,os.O_RDWR|os.O_NONBLOCK)
   child=None;perf=None
   try:
    argv=cmd(base,'counter',mode,work);child=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    assert select.select([child.stderr],[],[],10)[0] and child.stderr.readline()=='READY\n'
    pcmd=['taskset','-c','0','perf','stat','-j','--cputype','core','-e','instructions:u,cycles:u','-p',str(child.pid),'-D','-1','--control',f'fifo:{ctl},{ack}','-o',str(raw)]
    perf=subprocess.Popen(pcmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    def control(message):
     os.write(cf,(message+'\n').encode());assert select.select([af],[],[],10)[0],message;assert os.read(af,1024).rstrip(b'\0')==b'ack\n'
    control('enable');enabled=time.monotonic_ns();child.stdin.write('go\n');child.stdin.flush();lines=[];deadline=time.monotonic()+30
    while True:
     assert time.monotonic()<deadline,'child counter timeout'
     # readline safe here: fixed short output or a bounded kernel, producer timeout externally.
     line=child.stderr.readline();assert line,'counter child exited early'
     if line=='DONE\n':break
     lines.append(line)
    control('disable');disabled=time.monotonic_ns();child.stdin.write('stop\n');child.stdin.flush();stdout,stderr=child.communicate(timeout=10);assert child.returncode==0 and not stderr
    perf.send_signal(signal.SIGINT);po,pe=perf.communicate(timeout=10);assert perf.returncode in (0,-signal.SIGINT) and not po
    value=counts(raw.read_text());row=dict(base=base,mode=mode,work=work,repeat=rep,command=argv,perf_command=pcmd,counts=value,stdout=stdout,stderr=''.join(lines),perf_stderr=pe,enabled_ns=enabled,disabled_ns=disabled,status=child.returncode)
    results.append(row);(O/'counters.json').write_text(json.dumps(results,indent=2)+'\n')
   finally:
    for p in [child,perf]:
     if p is not None and p.poll() is None:p.kill();p.wait()
    for fd in [cf,af]:os.close(fd)
    ctl.unlink();ack.unlink()
  r=subprocess.run(cmd(base,'allocation',mode,work),capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stderr;lines=r.stderr.splitlines();assert lines[-1].startswith('ALLOC ');a=ast.literal_eval(lines[-1][6:]);alloc.append(dict(base=base,mode=mode,work=work,calls=a[0],allocated_bytes=a[1],live_bytes=a[2],peak_bytes=a[3],stdout=r.stdout,stderr=r.stderr));(O/'allocations.json').write_text(json.dumps(alloc,indent=2)+'\n')
  rf=O/'rss-current.txt';r=subprocess.run(['/usr/bin/time','-f','%M','-o',str(rf),*cmd(base,'primary',mode,work)],capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stderr;rss.append(dict(base=base,mode=mode,work=work,maxrss_kib=int(rf.read_text()),stdout=r.stdout,stderr=r.stderr));(O/'rss.json').write_text(json.dumps(rss,indent=2)+'\n');rf.unlink()
  print(label,'complete',flush=True)
