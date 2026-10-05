"""Reviewed READY/GO boundary diagnostic; unchanged target interval."""
import hashlib,json,os,pathlib,statistics,subprocess,sys
from jobs import LOCK
from handshake_jobs import HandshakeJobs
P=pathlib.Path(__file__).resolve().parent;out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False);j=HandshakeJobs(out/'jobs')
rows=[];blocks=[]
j.event('lock-acquired',phase='handshake-blocks',lock=LOCK,load1=os.getloadavg()[0])
try:
 j.run(['rustc','-O',P/'handshake_clock.rs','-o',P/'target/handshake-clock'],'build-handshake-clock',deadline=60)
 marker=out/'target-marker'
 cmd=[sys.executable,'-c',f'from pathlib import Path;Path({str(marker)!r}).write_text("ran")']
 def before_go():
  import time
  time.sleep(.05)
  assert not marker.exists(), 'target ran before GO'
 so,gaps=j.clock([P/'target/handshake-clock','1',str(len(cmd)),*cmd],'marker-before-GO',before_go=before_go)
 assert marker.read_text()=='ran'
 for repeat in range(3):
  for output in (['current','handshake'] if repeat%2==0 else ['handshake','current']):
   observer=4
   os.sched_setaffinity(0,{4})
   # Exactly the same target launch path proves the actual inherited affinity.
   target=[sys.executable,'-c','import os;print(sorted(os.sched_getaffinity(0)))']
   _,so,se=j.run(['taskset','-c','4',P/'target/clock','1',str(len(target)),*target],'affinity-control')
   v=so.decode().splitlines();assert len(v)==4 and v[1]=='0' and bytes.fromhex(v[2])==b'[4]\n' and not bytes.fromhex(v[3]) and not se
   for name,cmd,expected in [('true',['/bin/true'],b''),('cached',[str(P/'target/cached')],b'42\n')]:
    samples=[]
    for i in range(55):
     gaps={}
     if output=='current':
      _,so,se=j.run(['taskset','-c','4',P/'target/clock','1',str(len(cmd)),*cmd],'clock-'+name);assert not se
     else:so,gaps=j.clock(['taskset','-c','4',P/'target/handshake-clock','1',str(len(cmd)),*cmd],'clock-'+name)
     lines=so.decode().splitlines();assert len(lines)==4 and lines[1]=='0' and bytes.fromhex(lines[2])==expected and not bytes.fromhex(lines[3])
     ns=int(lines[0]);assert ns>0
     if i>=5:samples.append(ns);rows.append(dict(repeat=repeat,observer=observer,output=output,target=name,sample=i-5,ns=ns,**gaps))
    f=out/f'{repeat}-{output}-{name}-hyperfine.json'
    j.run(['taskset','-c','4','hyperfine','-N','--output','pipe','--warmup','5','--runs','50','--export-json',f,*cmd],'hyperfine-'+name,deadline=30)
    ref=statistics.median(json.loads(f.read_text())['results'][0]['times'])*1e9;med=statistics.median(samples)
    blocks.append(dict(repeat=repeat,observer=observer,output=output,target=name,median_ns=med,reference_ns=ref,difference_ns=med-ref,within_gate=abs(med-ref)<=150000))
    print(json.dumps(blocks[-1]),flush=True)
 value=dict(source_commit=subprocess.check_output(['git','-C',str(P.parents[1]),'rev-parse','HEAD'],text=True).strip(),clock_sha256=hashlib.sha256((P/'target/clock').read_bytes()).hexdigest(),handshake_clock_sha256=hashlib.sha256((P/'target/handshake-clock').read_bytes()).hexdigest(),rows=rows,blocks=blocks,sched_autogroup_enabled=pathlib.Path('/proc/sys/kernel/sched_autogroup_enabled').read_text(),cpu_policy={f.name:f.read_text() for f in pathlib.Path('/sys/devices/system/cpu/cpu4/cpufreq').glob('scaling_*') if f.is_file()})
 (out/'diagnostic.json').write_text(json.dumps(value,indent=2)+'\n')
finally:
 j.cleanup();j.event('lock-release',phase='handshake-blocks',lock=LOCK,load1=os.getloadavg()[0])
