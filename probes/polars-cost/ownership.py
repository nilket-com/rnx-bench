"""Sample native allocation/owner state and SIGINT during a real collect."""
import json,os,pathlib,re,select,signal,subprocess,tempfile,time
import polars as pl
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2]/'rnx';OUT=HERE.parents[1]/'results/polars-cost-0058';APP=ROOT/'adapters/polars/target/release/rnx-polars'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','POLARS_'))};ENV.update(TERM='xterm',NO_COLOR='1',POLARS_MAX_THREADS='1')
results={}
def snapshot(pid):
 root=pathlib.Path('/proc',str(pid));threads={};fds={}
 for f in (root/'task').glob('*/comm'):
  try:threads[f.parent.name]=f.read_text().strip()
  except FileNotFoundError:pass
 for f in (root/'fd').iterdir():
  try:fds[f.name]=os.readlink(f)
  except FileNotFoundError:pass
 return {'threads':threads,'fds':fds}
def read_until(p,token,timeout=30):
 data=b'';end=time.monotonic()+timeout
 while token not in data:
  remaining=end-time.monotonic();assert remaining>0,('timeout',data)
  readable,_,_=select.select([p.stdout],[],[],remaining);assert readable
  part=os.read(p.stdout.fileno(),65536);assert part,('closed',data,p.poll());data+=part
 return data.decode()
with tempfile.TemporaryDirectory(prefix='rnx-polars-owners-') as tmp:
 d=pathlib.Path(tmp);n=2_000_000
 frame=pl.DataFrame({'k':pl.int_range(n,0,-1,eager=True,dtype=pl.Int64),'v':pl.repeat(1,n,eager=True,dtype=pl.Int64)})
 csv=d/'large.csv';parquet=d/'large.parquet';frame.write_csv(csv);frame.write_parquet(parquet,compression='uncompressed');del frame
 env=dict(ENV,RNX_MEMORY_CEILING=str(16*1024*1024),RNX_CONFIG=str(d/'absent'),RNX_HISTORY=str(d/'history'))
 stderr=(d/'session.stderr').open('wb');p=subprocess.Popen([str(APP)],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr)
 try:
  def memory(source=''):
   p.stdin.write((source+':memory\n').encode());p.stdin.flush()
   text=read_until(p,b"not the session's share of anything.\n")
   match=re.search(r'tracked live allocation request bytes: (\d+) of a ceiling of (\d+)',text);assert match,text
   snap=snapshot(p.pid);assert not any(name.startswith('rnx-polars-') for name in snap['threads'].values()),snap
   assert str(csv) not in snap['fds'].values(),snap
   return {'text':text,'live':int(match[1]),'ceiling':int(match[2]),'owners':snap}
  before=memory()
  after=memory('let f={ let x=polars::read_csv('+json.dumps(str(csv))+',[("k","i64"),("v","i64")]).unwrap(); println!("NATIVE_RETURNED"); x };\n')
  assert 'NATIVE_RETURNED' in after['text'] and before['live']<before['ceiling']<after['live']
  assert after['live']-before['live']>=n*8,(before['live'],after['live'])
  assert 'evaluation is refused until :reset' in after['text']
  reset=memory('1\n:reset\n');assert after['live']-reset['live']>=n*8,(after['live'],reset['live'])
  assert len(reset['owners']['threads'])>len(before['owners']['threads'])
  p.stdin.write(b':q\n');p.stdin.flush();p.stdin.close();p.wait(timeout=15);assert p.returncode==0
  stderr.close();err=(d/'session.stderr').read_text();assert 'ceiling' in err
  results['allocation_and_lifetime']={'rows':n,'before':before,'after':after,'reset':reset,'stderr':err,'reaped':not pathlib.Path('/proc',str(p.pid)).exists()}
 finally:
  if p.poll() is None:p.kill();p.wait()
  stderr.close()
 source=d/'collect.rn';source.write_text('pub fn main(args) { let f=polars::read_parquet(args[0])?; let plan=f.lazy().group_by([polars::col("k")])?.agg([polars::col("v").sum()])?.sort(["k"])?; println!("COLLECT_START"); let result=plan.collect()?; println!("COLLECT_RETURNED"); }')
 traces=[]
 for label,interrupt,await_after in [("control",False,False),("interrupt-finish",True,False),("interrupt-await",True,True)]:
  active_source=source
  if await_after:
   active_source=d/'collect-async.rn'
   active_source.write_text(source.read_text().replace('pub fn main','pub async fn main').replace('println!("COLLECT_RETURNED");','println!("COLLECT_RETURNED"); time::sleep(100).await; println!("AFTER_AWAIT");'))
  errfile=(d/(label+'.stderr')).open('wb')
  p=subprocess.Popen([str(APP),'run',str(active_source),str(parquet)],env=ENV,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=errfile)
  try:
   prefix=read_until(p,b'COLLECT_START\n');start=time.perf_counter_ns();deadline=time.monotonic()+30
   active=None
   while time.monotonic()<deadline:
    if p.poll() is not None:break
    snap=snapshot(p.pid)
    if any(name.startswith('rnx-polars-') for name in snap['threads'].values()):active=snap;break
    time.sleep(.001)
   assert active is not None,'collect finished before a native thread could be observed'
   # Observe the engine owner still active after 50ms, then signal that call.
   time.sleep(.05);confirmed=snapshot(p.pid);assert any(name.startswith('rnx-polars-') for name in confirmed['threads'].values())
   sent=time.perf_counter_ns()
   if interrupt:p.send_signal(signal.SIGINT)
   tail=p.communicate(timeout=30)[0].decode();ended=time.perf_counter_ns();errfile.close()
   err=pathlib.Path(errfile.name).read_text()
   if await_after:assert p.returncode==130 and 'COLLECT_RETURNED' in tail and 'AFTER_AWAIT' not in tail,(p.returncode,tail,err)
   else:assert p.returncode==0 and 'COLLECT_RETURNED' in tail and not err,(p.returncode,tail,err)
   traces.append({'case':label,'interrupt':interrupt,'exit':p.returncode,'start_to_exit_ms':(ended-start)/1e6,'signal_or_control_checkpoint_to_exit_ms':(ended-sent)/1e6,'owner_at_checkpoint':confirmed,'stdout':prefix+tail,'stderr':err,'reaped':not pathlib.Path('/proc',str(p.pid)).exists()})
  finally:
   if p.poll() is None:p.kill();p.wait()
   errfile.close()
 results['collect']=traces
(OUT/'ownership.json').write_text(json.dumps(results,indent=2)+'\n')
print('PASS: sampled ceiling/native allocation, joined per-call threads, persistent engine pool, deferred SIGINT and reaping')
