"""Pre-registered launch-mode diagnostic; never a deciding Rune/Lua observation."""
import hashlib,json,os,pathlib,random,statistics,subprocess,sys
from jobs import Jobs
P=pathlib.Path(__file__).resolve().parent
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False);os.sched_setaffinity(0,{4});j=Jobs(out/'jobs')
commands={'true':['/bin/true'],'cached':[str(P/'target/cached')]};modes=['ordinary','new-session','owned-group','journaled-session','journaled-observer0'];rows=[]
options={'ordinary':{},'new-session':{'start_new_session':True},'owned-group':{'process_group':0}}
j.event('lock-acquired',phase='clock-diagnostic',load1=os.getloadavg()[0])
try:
 for mode,opts in options.items():
  p=subprocess.Popen(['/bin/sleep','.1'],**opts)
  try:
   info={'mode':mode,'pid':p.pid,'sid':os.getsid(p.pid),'pgid':os.getpgid(p.pid),'autogroup':pathlib.Path(f'/proc/{p.pid}/autogroup').read_text()}
   (out/(mode+'-group.json')).write_text(json.dumps(info))
  finally:p.wait(timeout=2)
 def observe(mode,name):
  cmd=commands[name];argv=[str(P/'target/clock'),'1',str(len(cmd)),*cmd]
  if mode in ('journaled-session','journaled-observer0'):
   affinity=os.sched_getaffinity(0)
   if mode=='journaled-observer0':os.sched_setaffinity(0,{0});argv=['taskset','-c','4',*argv]
   try:_,so,se=j.run(argv,'clock-'+name,deadline=10)
   finally:os.sched_setaffinity(0,affinity)
  else:
   r=subprocess.run(argv,capture_output=True,timeout=10,**options[mode]);assert r.returncode==0;so,se=r.stdout,r.stderr
  assert not se
  lines=so.decode().splitlines();assert len(lines)==4 and lines[1]=='0' and bytes.fromhex(lines[3])==b''
  assert bytes.fromhex(lines[2])==(b'' if name=='true' else b'42\n')
  ns=int(lines[0]);assert ns>0
  return ns
 for mode in modes:
  for name in commands:
   for _ in range(5):observe(mode,name)
 tasks=[(mode,name,i) for mode in modes for name in commands for i in range(50)];random.Random(16966).shuffle(tasks)
 for mode,name,i in tasks:rows.append(dict(mode=mode,target=name,sample=i,ns=observe(mode,name)))
 reference={}
 for name,cmd in commands.items():
  f=out/(name+'-hyperfine.json');j.run(['hyperfine','-N','--warmup','5','--runs','50','--export-json',f,*cmd],'hyperfine-'+name,deadline=30)
  reference[name]=statistics.median(json.loads(f.read_text())['results'][0]['times'])*1e9
 summary=[dict(mode=mode,target=name,median_ns=statistics.median(r['ns'] for r in rows if r['mode']==mode and r['target']==name),reference_ns=reference[name]) for mode in modes for name in commands]
 for r in summary:r['difference_ns']=r['median_ns']-r['reference_ns'];r['within_gate']=abs(r['difference_ns'])<=150000
 value=dict(clock_sha256=hashlib.sha256((P/'target/clock').read_bytes()).hexdigest(),rows=rows,summary=summary,affinity=list(os.sched_getaffinity(0)),cpu_policy={f.name:f.read_text() for f in pathlib.Path('/sys/devices/system/cpu/cpu4/cpufreq').glob('scaling_*') if f.is_file()})
 (out/'diagnostic.json').write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps(summary,indent=2))
finally:
 j.cleanup();j.event('lock-release',phase='clock-diagnostic',load1=os.getloadavg()[0])
