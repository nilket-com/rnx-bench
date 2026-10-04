"""Registered round-3 counter gate. Product binary and sources remain unchanged."""
import importlib.util,json,math,os,pathlib,select,signal,statistics,subprocess,sys,time,threading
H=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('slots',H/'diagnose_slots.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
m=d.m
PIN=d.PIN

def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def perf_counts(raw):
 rows=[json.loads(x) for x in raw.splitlines() if x.strip()];assert len(rows)==2,rows
 result={}
 for r in rows:
  event=r['event'];key=next((k for k in ('instructions','cycles') if event in (k+':u','cpu_core/'+k+'/u')),None)
  assert key and key not in result,r
  n=float(r['counter-value']);pct=float(r['pcnt-running'])
  assert math.isfinite(n) and n>0 and pct>=99 and float(r['event-runtime'])>0,r
  result[key]=n
 assert set(result)=={'instructions','cycles'}
 return result

def load(out,server,slot,ka,seconds,label,measured=False):
 cmd=['taskset','-c',m.b.LOAD_CPUS,'oha','--no-tui','--output-format','json','-z',f'{seconds}s','-c','1','-w','--http-version','1.1']
 if not ka:cmd+=['--disable-keepalive']
 cmd+=[f'http://127.0.0.1:{m.b.PORTS[slot]}/hello/world']
 perf=None;fds=[];sample={};thread=None;window={}
 try:
  if measured:
   ctl=out/(label+'.ctl');ack=out/(label+'.ack');os.mkfifo(ctl);os.mkfifo(ack)
   cf=os.open(ctl,os.O_RDWR|os.O_NONBLOCK);af=os.open(ack,os.O_RDWR|os.O_NONBLOCK);fds=[cf,af]
   tids=sorted(int(p.name) for p in pathlib.Path(f'/proc/{server.pid}/task').iterdir())
   pcmd=['perf','stat','-j','--cputype','core','-e','instructions:u,cycles:u','-p',str(server.pid),'-D','-1','--control',f'fifo:{ctl},{ack}','-o',str(out/(label+'.perf-raw.jsonl'))]
   perf=subprocess.Popen(pcmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   def control(s):
    os.write(cf,(s+'\n').encode());assert select.select([af],[],[],5)[0],s
    assert os.read(af,1024).rstrip(b'\0')==b'ack\n',s
   control('enable');window['enabled_ns']=time.monotonic_ns()
   def probe():time.sleep(5);sample['connections']=m.b.established(m.b.PORTS[slot])
   thread=threading.Thread(target=probe);thread.start()
  began=time.monotonic_ns();p=subprocess.run(cmd,capture_output=True,text=True,timeout=seconds+20);ended=time.monotonic_ns()
  artifact={'argv':cmd,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'result':json.loads(p.stdout)}
  save(out/(label+'.oha.json'),artifact);assert p.returncode==0
  if measured:
   control('disable');window['disabled_ns']=time.monotonic_ns();window.update(oha_spawn_ns=began,oha_exit_ns=ended)
   perf.send_signal(signal.SIGINT);stdout,stderr=perf.communicate(timeout=5)
   thread.join(timeout=1);assert not thread.is_alive()
   raw=(out/(label+'.perf-raw.jsonl')).read_text()
   pa={'argv':pcmd,'exit':perf.returncode,'stdout':stdout,'stderr':stderr,'raw':raw,'window':window,'tids':tids}
   save(out/(label+'.perf.json'),pa);assert perf.returncode in (0,-signal.SIGINT)
   counts=perf_counts(raw)
  values=m.b.validate(artifact['result'],1,ka,sample.get('connections') if measured else (1 if ka else None))
  if measured:return {**values,'connections':sample.get('connections'),'counts':counts,'per_request':{k:v/values['successful'] for k,v in counts.items()}}
 finally:
  if perf and perf.poll() is None:perf.kill();perf.wait()
  if thread:thread.join(timeout=6)
  for fd in fds:os.close(fd)
  for ext in ('ctl','ack'):
   p=out/(label+'.'+ext)
   if p.exists():p.unlink()

def validate(root):
 reg=json.loads((root/'registration.json').read_text());assert reg['binary_sha256']==PIN and reg['server_cpus']==m.b.SERVER_CPUS and reg['load_cpus']==m.b.LOAD_CPUS
 assert reg['repetitions']==3 and reg['old_slots']=='ABBA' and reg['orders']==['ON','NO','NO','ON']
 rows=json.loads((root/'rows.json').read_text());expected=[]
 for ka in (False,True):
  for rep in range(3):
   for block,old_slot in enumerate('ABBA'):
    out=root/f'ka-{int(ka)}-rep-{rep}-block-{block}'
    mapping={slot:('before.rn' if slot==old_slot else 'after.rn') for slot in 'AB'}
    assert json.loads((out/'sources.json').read_text())==mapping
    for slot,name in mapping.items():assert m.sha(out/'sources'/('before.rn' if slot=='A' else 'after.rn'))==m.sha(H/name)
    for source in (('old','new') if block in (0,3) else ('new','old')):
     slot=old_slot if source=='old' else ('B' if old_slot=='A' else 'A');expected.append((ka,rep,block,slot,source))
     row=rows[len(expected)-1];assert (row['ka'],row['rep'],row['block'],row['slot'],row['source'])==expected[-1]
     for warm in (True,False):
      label=source+('-warm' if warm else '');a=json.loads((out/(label+'.oha.json')).read_text())
      assert a['exit']==0 and json.loads(a['stdout'])==a['result']
      cmd=['taskset','-c',m.b.LOAD_CPUS,'oha','--no-tui','--output-format','json','-z',('3s' if warm else '10s'),'-c','1','-w','--http-version','1.1']
      if not ka:cmd+=['--disable-keepalive']
      cmd+=[f'http://127.0.0.1:{m.b.PORTS[slot]}/hello/world'];assert a['argv']==cmd
      v=m.b.validate(a['result'],1,ka,(1 if warm and ka else row['connections']))
      if not warm:assert all(row[k]==v[k] for k in v)
     a=json.loads((out/(source+'.perf.json')).read_text());raw=(out/(source+'.perf-raw.jsonl')).read_text()
     assert raw==a['raw'] and a['exit'] in (0,-signal.SIGINT) and a['tids']
     argv=a['argv'];assert argv[:7]==['perf','stat','-j','--cputype','core','-e','instructions:u,cycles:u']
     assert argv[7]=='-p' and int(argv[8]) in a['tids'] and argv[9:12]==['-D','-1','--control']
     assert argv[12:]==[f'fifo:{out/(source+".ctl")},{out/(source+".ack")}','-o',str(out/(source+'.perf-raw.jsonl'))]
     w=a['window'];assert w['enabled_ns']<=w['oha_spawn_ns']<w['oha_exit_ns']<=w['disabled_ns']
     assert 9.5<(w['oha_exit_ns']-w['oha_spawn_ns'])/1e9<15
     c=perf_counts(raw);assert c==row['counts'] and {k:v/row['successful'] for k,v in c.items()}==row['per_request']
 assert len(rows)==len(expected)==48
 print('48 measured rows, 96 oha artifacts, 48 raw perf artifacts and all bindings PASS',flush=True)

def decision(root):
 rows=json.loads((root/'rows.json').read_text());assert len(rows)==48
 summaries=[];bad=[]
 for ka in (False,True):
  med={}
  for source in ('old','new'):
   rr=[r for r in rows if r['ka']==ka and r['source']==source];assert len(rr)==12
   med[source]={}
   for metric in ('instructions','cycles'):
    vs=[r['per_request'][metric] for r in rr];md=statistics.median(vs);spread=(max(vs)-min(vs))/md
    med[source][metric]=md
    if metric=='instructions' and spread>.05:bad.append(f'{ka}/{source}/{metric} spread {spread}')
    summaries.append({'ka':ka,'source':source,'metric':metric,'median':md,'range':[min(vs),max(vs)],'spread':spread})
  ir=med['new']['instructions']/med['old']['instructions'];cr=med['new']['cycles']/med['old']['cycles']
  if (ir-1)*(cr-1)<0 and abs(ir-cr)>.03:bad.append(f'{ka} opposite ratios {ir}/{cr}')
  summaries.append({'ka':ka,'instructions_ratio':ir,'cycles_ratio':cr})
 ratios=[s['instructions_ratio'] for s in summaries if 'instructions_ratio'in s]
 verdict='C' if bad else ('A' if all(x<=1.03 for x in ratios) else ('B' if ratios[0]>1.03 else 'C'))
 save(root/'decision.json',{'decision':verdict,'inconsistencies':bad,'summaries':summaries});print(verdict,json.dumps(summaries),flush=True)

def main(root):
 root=root.resolve();root.mkdir(parents=True,exist_ok=False)
 assert m.sha(m.STOCK)==PIN
 topology={x:pathlib.Path('/sys/bus/event_source/devices/'+x+'/cpus').read_text().strip() for x in ('cpu_core','cpu_atom')};assert topology['cpu_core']=='0-15'
 save(root/'registration.json',{'binary_sha256':PIN,'topology':topology,'server_cpus':m.b.SERVER_CPUS,'load_cpus':m.b.LOAD_CPUS,'repetitions':3,'old_slots':'ABBA','orders':['ON','NO','NO','ON'],'window':'acknowledged enable before oha spawn, disable after oha exit; launch/exit envelope included; warmup excluded'})
 rows=[]
 try:
  for ka in (False,True):
   for rep in range(3):
    for block,old_slot in enumerate('ABBA'):
     out=root/f'ka-{int(ka)}-rep-{rep}-block-{block}';out.mkdir();sources=out/'sources';sources.mkdir()
     mapping={s:('before.rn' if s==old_slot else 'after.rn') for s in 'AB'}
     for s,name in mapping.items():(sources/('before.rn' if s=='A' else 'after.rn')).write_bytes((H/name).read_bytes())
     save(out/'sources.json',mapping);m.HERE=sources;procs={};logs={}
     try:
      for s in 'AB':procs[s]=m.start(s,out,logs)[0]
      for source in (('old','new') if block in (0,3) else ('new','old')):
       s=old_slot if source=='old' else ('B' if old_slot=='A' else 'A')
       load(out,procs[s],s,ka,3,source+'-warm')
       values=load(out,procs[s],s,ka,10,source,True)
       row={'ka':ka,'rep':rep,'block':block,'slot':s,'source':source,**values};rows.append(row);print(json.dumps(row),flush=True)
     finally:
      for p in procs.values():
       if p.poll() is None:p.terminate()
       p.wait(timeout=15)
      for f in logs.values():f.close()
 finally:save(root/'rows.json',rows)
 decision(root)
if __name__=='__main__':
 if sys.argv[1]=='--validate':validate(pathlib.Path(sys.argv[2]).resolve())
 elif sys.argv[1]=='--decision':decision(pathlib.Path(sys.argv[2]))
 else:main(pathlib.Path(sys.argv[1]))
