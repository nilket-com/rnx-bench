"""Reviewed observer-core calibration: fixed placements in matched reversed blocks."""
import hashlib,json,os,pathlib,statistics,subprocess,sys
from jobs import Jobs,LOCK
P=pathlib.Path(__file__).resolve().parent;out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False);j=Jobs(out/'jobs')
rows=[];blocks=[]
j.event('lock-acquired',phase='observer-blocks',lock=LOCK,load1=os.getloadavg()[0])
try:
 for repeat in range(3):
  for observer in ([4,0] if repeat%2==0 else [0,4]):
   os.sched_setaffinity(0,{observer})
   # Exactly the same target launch path proves the actual inherited affinity.
   target=[sys.executable,'-c','import os;print(sorted(os.sched_getaffinity(0)))']
   _,so,se=j.run(['taskset','-c','4',P/'target/clock','1',str(len(target)),*target],'affinity-control')
   v=so.decode().splitlines();assert len(v)==4 and v[1]=='0' and bytes.fromhex(v[2])==b'[4]\n' and not bytes.fromhex(v[3]) and not se
   for name,cmd,expected in [('true',['/bin/true'],b''),('cached',[str(P/'target/cached')],b'42\n')]:
    samples=[]
    for i in range(55):
     _,so,se=j.run(['taskset','-c','4',P/'target/clock','1',str(len(cmd)),*cmd],'clock-'+name)
     lines=so.decode().splitlines();assert len(lines)==4 and lines[1]=='0' and bytes.fromhex(lines[2])==expected and not bytes.fromhex(lines[3]) and not se
     ns=int(lines[0]);assert ns>0
     if i>=5:samples.append(ns);rows.append(dict(repeat=repeat,observer=observer,target=name,sample=i-5,ns=ns))
    f=out/f'{repeat}-{observer}-{name}-hyperfine.json'
    j.run(['taskset','-c','4','hyperfine','-N','--warmup','5','--runs','50','--export-json',f,*cmd],'hyperfine-'+name,deadline=30)
    ref=statistics.median(json.loads(f.read_text())['results'][0]['times'])*1e9;med=statistics.median(samples)
    blocks.append(dict(repeat=repeat,observer=observer,target=name,median_ns=med,reference_ns=ref,difference_ns=med-ref,within_gate=abs(med-ref)<=150000))
    print(json.dumps(blocks[-1]),flush=True)
 value=dict(source_commit=subprocess.check_output(['git','-C',str(P.parents[1]),'rev-parse','HEAD'],text=True).strip(),clock_sha256=hashlib.sha256((P/'target/clock').read_bytes()).hexdigest(),rows=rows,blocks=blocks,sched_autogroup_enabled=pathlib.Path('/proc/sys/kernel/sched_autogroup_enabled').read_text(),cpu_policy={f.name:f.read_text() for f in pathlib.Path('/sys/devices/system/cpu/cpu4/cpufreq').glob('scaling_*') if f.is_file()})
 (out/'diagnostic.json').write_text(json.dumps(value,indent=2)+'\n')
finally:
 j.cleanup();j.event('lock-release',phase='observer-blocks',lock=LOCK,load1=os.getloadavg()[0])
