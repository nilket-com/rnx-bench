"""Bounded formatter resources, controls and demo parity. No network or adapter loads."""
import hashlib,json,pathlib,resource as usage,subprocess,sys,time
B=pathlib.Path(__file__).resolve().parents[2];R=B.parent/'rnx'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def resource(binary,args,out,source=None):
 before=usage.getrusage(usage.RUSAGE_CHILDREN);start=time.monotonic();p=subprocess.Popen([str(binary),*map(str,args)],stdin=subprocess.PIPE if source is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 if source is not None:p.stdin.write(source);p.stdin.close();p.stdin=None
 peak={};threads=set()
 while p.poll() is None:
  try:
   for pid in pathlib.Path(f'/proc/{p.pid}/task/{p.pid}/children').read_text().split():
    for line in pathlib.Path('/proc/'+pid+'/status').read_text().splitlines():
     k,_,value=line.partition(':')
     if k in ('VmPeak','VmSize','VmRSS','VmHWM'):peak[k]=max(peak.get(k,0),int(value.split()[0]))
     if k=='Threads':threads.add(int(value.strip()))
  except (OSError,ValueError):pass
  time.sleep(.001)
 stdout,stderr=p.communicate(timeout=8);after=usage.getrusage(usage.RUSAGE_CHILDREN)
 result={'argv':[str(binary),*map(str,args)],'binary_sha256':sha(binary),'cpu_user_seconds':after.ru_utime-before.ru_utime,'cpu_system_seconds':after.ru_stime-before.ru_stime,'cpu_scope':'entire CLI and reaped worker, an upper bound on worker CPU','source':source,'exit':p.returncode,'elapsed':time.monotonic()-start,'worker_peak_kib':peak,'worker_threads':sorted(threads),'stdout':stdout,'stderr':stderr}
 save(out,result);return result

def main(stock,test,out):
 out.mkdir(parents=True,exist_ok=False);size=0;parts=[];n=0
 while True:
  s=f'fn f{n}(){{let value={n};if value>0{{println!("value {{}}",value);}}let items=[1,2,3];for x in items{{let y=x+1;}}}}\n'
  if size+len(s)>=1024*1024:break
  parts.append(s);size+=len(s);n+=1
 prefix='fn last(){let s=\"';suffix='\";}\n'
 large=out/'capacity.rn';large.write_text(''.join(parts)+prefix+'x'*(1024*1024-1-size-len(prefix)-len(suffix))+suffix)
 save(out/'inputs.json',{'capacity_sha256':sha(large),'capacity_bytes':large.stat().st_size,'functions':n+1,'stock_sha256':sha(stock),'test_support_sha256':sha(test)})
 for name,args in [('capacity',['fmt','--check',large]),('typical',['fmt','--check',B/'probes/web-0166/after.rn'])]:
  a=resource(stock,args,out/(name+'.json'));assert a['exit']==1 and not a['stderr'] and a['worker_threads']==[1]
 for mode,source in [('lean','fn a(){}'),('completion','pub fn main(){foo(1,'),('allocation','pub fn main(){println!("x",'),('overflow',''),('panic',''),('timeout',''),('malformed','')]:
  a=resource(test,['--rnx-fmt-test',mode],out/(mode+'.json'),source);assert a['exit']==(0 if mode in ('lean','completion') else 2)
  if mode=='lean':assert json.loads(a['stdout'])=={'threads':1,'contexts':0}
  if mode=='timeout':assert 'killed and reaped' in a['stderr'] and a['elapsed']<7
 controls=[]
 for name,source in [('template-open','pub fn main(){let x=`a { b`;}'),('template-close','pub fn main(){let x=`a } b`;}'),('template-backtick',r'pub fn main(){let x=`a \` b`;}'),('joined-words','a\nb'),('joined-expression','pub fn main(){let x=a\n// c\nb;}'),('stray-hash','# !')]:
  target=out/(name+'.rn');target.write_text(source)
  a=resource(stock,['fmt',target],out/(name+'.json'));assert a['exit']==2 and not a['stdout'] and target.read_text()==source
  controls.append(name)
 save(out/'upstream-controls.json',controls)
 rows=[]
 for source in sorted((R/'demos').rglob('*.rn')):
  p=subprocess.run([str(stock),'fmt','--stdin'],input=source.read_bytes(),capture_output=True,timeout=7);assert p.returncode==0 and not p.stderr
  target=out/('demo-'+source.parent.name+'-'+source.name);target.write_bytes(p.stdout)
  assert subprocess.run([str(stock),'fmt','--check',str(target)],capture_output=True).returncode==0
  row={'path':str(source.relative_to(R)),'before_sha256':sha(source),'after_sha256':sha(target)}
  if source.parent.name=='demos':
   a=subprocess.run([str(stock),'run',str(source)],cwd=R,capture_output=True,timeout=15);b=subprocess.run([str(stock),'run',str(target)],cwd=R,capture_output=True,timeout=15)
   assert (a.returncode,a.stdout,a.stderr)==(b.returncode,b.stdout,b.stderr);row['run_identical']=True
  rows.append(row)
 save(out/'demos.json',rows);print('capacity, latency, 7 worker controls, 6 demos and 3 offline outputs PASS')
if __name__=='__main__':main(pathlib.Path(sys.argv[1]).resolve(),pathlib.Path(sys.argv[2]).resolve(),pathlib.Path(sys.argv[3]).resolve())
