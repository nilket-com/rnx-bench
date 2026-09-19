"""Production shared-entry code; tiny Cargo assembly, real processes and signals."""
from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,tempfile,time
H=Path('/home/me/work/rnx-bench/probes/git-source-workflow/target/publication-replay');B=Path('/home/me/work/rnx-bench');R=B.parent/'rnx';O=Path('/home/me/work/rnx-bench/results/git-source-workflow-0067/publication-replay');T=H/'target/tool/target/release/rnx-cache-publication-probe'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_'))};rows={};children=[]
def call(args,env,cwd=None,ok=True):
 p=subprocess.run(list(map(str,args)),env=env,cwd=cwd,capture_output=True,text=True,timeout=90)
 if ok:assert p.returncode==0,(args,p.stdout,p.stderr)
 return p
def wait_for(fn, label, timeout=30):
 end=time.monotonic()+timeout
 while not fn():
  assert time.monotonic()<end,label
  time.sleep(.01)
def sha(b):return hashlib.sha256(b).hexdigest()
def stopped(pid):
 p=Path('/proc')/str(pid)/'stat'
 return not p.exists() or p.read_text().split()[2]=='Z'
oldmask=os.umask(0o077)
try:
 with tempfile.TemporaryDirectory(prefix='rnx-cache-publication-') as tmp:
  root=Path(tmp);cache=root/'cache';cache.mkdir();home=root/'cargo';home.mkdir();env=dict(ENV,CARGO_HOME=str(home));n=root/'native';shim=root/'shim';shim.mkdir()
  cargo=call(['rustup','which','cargo'],env).stdout.strip();rustc=call(['rustup','which','rustc'],env).stdout.strip()
  log=root/'compiler.jsonl'
  for name,real in [('cargo',cargo),('rustc',rustc)]:
   script='#!/usr/bin/python3\nimport os,sys,json\n'
   script+=f'name={name!r}; real={real!r}\n'
   script+='with open(os.environ["RNX_COMPILER_LOG"],"a") as f:f.write(json.dumps({"program":name,"args":sys.argv[1:]})+"\\n")\n'
   script+='if os.getenv("RNX_FORBID_BUILD") and ((name=="cargo" and sys.argv[1] not in ["-V"]) or (name=="rustc" and "--crate-name" in sys.argv)):sys.exit(93)\n'
   script+='os.execv(real,[real]+sys.argv[1:])\n'
   (shim/name).write_text(script);(shim/name).chmod(0o700)
  env.update(PATH=str(shim)+':'+env['PATH'],RNX_COMPILER_LOG=str(log))
  for name in ['runtime','adapter']:(n/name/'src').mkdir(parents=True)
  (n/'runtime/Cargo.toml').write_text('[package]\nname="rnx"\nversion="0.0.0"\nedition="2024"\n[features]\nproject-sources=[]\ncount-allocations=[]\n')
  (n/'runtime/src/lib.rs').write_text('pub struct Extensions(Vec<fn()->String>);impl Extensions{pub fn none()->Self{Self(vec![])}pub fn with(mut self,_:&str,b:fn()->String)->Self{self.0.push(b);self}}pub fn main_with(e:Extensions)->Result<(),Box<dyn std::error::Error>>{for b in e.0{println!("{}",b());}println!("source={}",std::fs::read_to_string("main.rn")?);Ok(())}\n')
  (n/'adapter/Cargo.toml').write_text('[package]\nname="publication-adapter"\nversion="0.0.0"\nedition="2024"\n')
  (n/'adapter/src/lib.rs').write_text('pub fn build()->String{std::fs::read_to_string(concat!(env!("OUT_DIR"),"/retained.txt")).unwrap()}\n')
  (n/'adapter/build.rs').write_text('fn main(){let out=std::env::var("OUT_DIR").unwrap();std::fs::write(format!("{out}/retained.txt"),"retained").unwrap();if let Ok(p)=std::env::var("RNX_BUILD_HOLD"){std::fs::write(&p,std::process::id().to_string()).unwrap();while std::path::Path::new(&p).exists(){std::thread::sleep(std::time::Duration::from_millis(10));}}}\n')
  call(['git','init','--quiet',n],env);call(['git','-C',n,'add','.'],env)
  apps=[]
  for label in ['a','b','c']:
   app=root/label;app.mkdir();(app/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath='+json.dumps(str(n/'runtime'))+'\n[native.probe]\npath='+json.dumps(str(n/'adapter'))+'\npackage="publication-adapter"\nbuilder="build"\nhook="plain"\n');(app/'main.rn').write_text('app-'+label);(app/'fixture-locked').write_text('lock-v1');apps.append(app)
  stage=cache/'resolve/base/assembly';stage.mkdir(parents=True)
  call([T,'prepare',cache,stage,apps[0]],env)
  meta=call(['cargo','metadata','--offline','--format-version','1'],env,stage).stdout;(root/'metadata.json').write_text(meta)
  rustcv=call(['rustc','-Vv'],env,stage).stdout;cargov=call(['cargo','-V'],env,stage).stdout
  context={'cache_root':str(cache),'cargo_home':str(home),'rustup_home':None,'rustup_toolchain':None,'rustc':rustcv,'cargo':cargov,'target':next(x[6:] for x in rustcv.splitlines() if x.startswith('host: ')),'profile':'release','features':['project-sources']}
  (root/'context.json').write_text(json.dumps(context))
  identity=json.loads(call([T,'identity',cache,stage,apps[0],root/'metadata.json',home,root/'context.json',stage/'Cargo.lock'],env).stdout)
  ip=root/'identity.json';ip.write_text(identity['canonical']);key=identity['key'];entry=cache/'entries'/key
  def events():return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
  def builds(es):return sum(e['program']=='cargo' and e['args'][0]=='build' for e in es)
  def start(app=apps[0],extra=None,idpath=ip,lockpath=stage/'Cargo.lock'):
   out=open(root/f'out-{len(children)}','w+');err=open(root/f'err-{len(children)}','w+');p=subprocess.Popen([T,'entry',idpath,lockpath,app],env=dict(env,**(extra or {})),stdout=out,stderr=err,stdin=subprocess.DEVNULL);children.append((p,out,err));return children[-1]
  def finish(t,ok=True):
   p,out,err=t;status=p.wait(timeout=90);out.seek(0);err.seek(0);o=out.read();e=err.read()
   if ok:assert status==0,(status,o,e)
   else:assert status!=0,(o,e)
   return {'status':status,'stdout':o,'stderr':e}
  def receipt(app):return json.loads((app/'fixture-receipt.json').read_text())
  def reset():
   traces=O/'compiler-traces';traces.mkdir(exist_ok=True)
   if log.exists():shutil.copyfile(log,traces/f'{len(list(traces.iterdir())):03d}.jsonl')
   if entry.exists():shutil.rmtree(entry)
   for app in apps:
    for name in ['fixture-receipt.json','fixture-receipt.new']:(app/name).unlink(missing_ok=True)
   log.write_text('')
  # Two actual projects, one build, each reads its own application from its cwd.
  hold=root/'hold';a=start(extra={'RNX_BUILD_HOLD':str(hold)});wait_for(hold.exists,'builder active');waiter=root/'waiting';b=start(apps[1],{'RNX_CACHE_PAUSE':'waiting','RNX_CACHE_MARKER':str(waiter)});wait_for(waiter.exists,'waiter blocked');waiter.unlink();hold.unlink();ra=finish(a);rb=finish(b)
  assert builds(events())==1 and receipt(apps[0])['path']==receipt(apps[1])['path'] and not receipt(apps[0])['hit'] and receipt(apps[1])['hit']
  outputs=[call([receipt(app)['path']],env,app).stdout for app in apps[:2]];assert 'source=app-a' in outputs[0] and 'source=app-b' in outputs[1]
  print('same-key passed',flush=True)
  rows['same-key']={'builds':builds(events()),'outputs':outputs,'builder':ra,'waiter':rb}
  before=len(events());hit=finish(start(apps[2],{'RNX_FORBID_BUILD':'1'}));assert builds(events()[before:])==0 and receipt(apps[2])['hit'];rows['hit-compiler-trap']=hit
  # Positive control for the compilation trap.
  reset();rows['miss-compiler-trap']=finish(start(extra={'RNX_FORBID_BUILD':'1'}),False);assert not (entry/'ready.json').exists()
  # SIGTERM is the owned Cargo process-group interruption contract. No extra runtime/drain.
  for sig in [signal.SIGTERM,signal.SIGINT]:
   reset();hold=root/'hold';a=start(extra={'RNX_BUILD_HOLD':str(hold)});wait_for(hold.exists,'build script active');pid=int(hold.read_text());assert all(str(cache/'locks'/f'{key}.lock')!=os.readlink(f) for f in Path('/proc',str(pid),'fd').iterdir());waiter=root/'waiting';b=start(apps[1],{'RNX_CACHE_PAUSE':'waiting','RNX_CACHE_MARKER':str(waiter)});wait_for(waiter.exists,'waiter blocked');a[0].send_signal(sig);ra=finish(a,False);assert ra['status']==128+sig;wait_for(lambda:stopped(pid),'build child reaped');assert not (entry/'ready.json').exists() and not (apps[0]/'fixture-receipt.json').exists();hold.unlink();waiter.unlink();rb=finish(b);assert not receipt(apps[1])['hit'] and builds(events())==2;print('builder',sig.name,'passed',flush=True);rows['builder-'+sig.name]={'builder':ra,'waiter':rb,'child_pid':pid,'builds':2}
  # Killing a waiter must never cancel the unrelated lock holder.
  for sig in [signal.SIGTERM,signal.SIGKILL]:
   reset();a=start(extra={'RNX_BUILD_HOLD':str(hold)});wait_for(hold.exists,'builder active');pid=int(hold.read_text());assert all(str(cache/'locks'/f'{key}.lock')!=os.readlink(f) for f in Path('/proc',str(pid),'fd').iterdir());waiter=root/'waiting';b=start(apps[1],{'RNX_CACHE_PAUSE':'waiting','RNX_CACHE_MARKER':str(waiter)});wait_for(waiter.exists,'waiter blocked');b[0].send_signal(sig);rb=finish(b,False);assert not stopped(pid) and not (apps[1]/'fixture-receipt.json').exists();hold.unlink();waiter.unlink();ra=finish(a);rc=finish(start(apps[2],{'RNX_FORBID_BUILD':'1'}));assert receipt(apps[2])['hit'] and builds(events())==1;print('waiter',sig.name,'passed',flush=True);rows['waiter-'+sig.name]={'waiter':rb,'builder':ra,'next':rc,'builds':1}
  # Distinct identities have no shared build mutex (overlapping real build scripts).
  reset();doc=json.loads(ip.read_text());doc['main']=doc['main'].replace('"probe"','"different"');ip2=root/'identity2.json';ip2.write_text(json.dumps(doc,separators=(',',':')));h2=root/'hold2';a=start(extra={'RNX_BUILD_HOLD':str(hold)});wait_for(hold.exists,'key one active');b=start(apps[1],{'RNX_BUILD_HOLD':str(h2)},idpath=ip2);wait_for(h2.exists,'key two progresses without release of key one');assert not stopped(int(hold.read_text()));hold.unlink();h2.unlink();ra=finish(a);rb=finish(b);assert receipt(apps[0])['key']!=receipt(apps[1])['key'];rows['two-keys']={'builds':builds(events()),'a':ra,'b':rb}
  # All publication boundaries, with a retry proving unpublished data isn't a hit.
  for point in ['before-build','after-build','before-ready','ready-written','after-ready','before-attach']:
   reset();bad=finish(start(extra={'RNX_CACHE_FAIL':point}),False);published=point in ['after-ready','before-attach'];assert (entry/'ready.json').exists()==published and not (apps[0]/'fixture-receipt.json').exists();good=finish(start(apps[1],{'RNX_FORBID_BUILD':'1'} if published else None));assert receipt(apps[1])['hit']==published;print('failure',point,'passed',flush=True);rows['failure-'+point]={'failed':bad,'retry':good,'ready_after_failure':published}
  reset();bad=finish(start(extra={'RNX_FIXTURE_ATTACH_FAIL':'1'}),False);assert (entry/'ready.json').exists() and not (apps[0]/'fixture-receipt.json').exists();good=finish(start(apps[1],{'RNX_FORBID_BUILD':'1'}));rows['attachment-failure']={'failed':bad,'retry':good}
  # Edits observed after waiting/building: native/config forbid ready, project only forbids receipt.
  for label,path in [('native',n/'adapter/src/lib.rs'),('config',home/'config.toml'),('config-managed',entry/'assembly/.cargo/config.toml'),('source',apps[0]/'main.rn'),('lock',apps[0]/'fixture-locked')]:
   reset();old=path.read_bytes() if path.exists() else None;mark=root/'pause';a=start(extra={'RNX_CACHE_PAUSE':'after-build','RNX_CACHE_MARKER':str(mark)});wait_for(mark.exists,label+' pause');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'[net]\noffline=true\n' if label.startswith('config') else (old or b'')+b'\n// edit\n');mark.unlink();bad=finish(a,False);assert not (apps[0]/'fixture-receipt.json').exists();assert (entry/'ready.json').exists()==(label in ['source','lock']);rows['edit-'+label]=bad
   if old is None:path.unlink()
   else:path.write_bytes(old)
  reset();a=start(extra={'RNX_BUILD_HOLD':str(hold)});wait_for(hold.exists,'builder active');waiter=root/'waiting';b=start(apps[1],{'RNX_CACHE_PAUSE':'waiting','RNX_CACHE_MARKER':str(waiter)});wait_for(waiter.exists,'waiter active');old=(apps[1]/'main.rn').read_bytes();(apps[1]/'main.rn').write_bytes(old+b' edited');hold.unlink();finish(a);waiter.unlink();rows['waiter-revalidation']=finish(b,False);assert not (apps[1]/'fixture-receipt.json').exists() and builds(events())==1;(apps[1]/'main.rn').write_bytes(old)
  # Ready entries are never silently repaired; full known-digest validation on hits.
  reset();finish(start());ready=entry/'ready.json';saved=ready.read_bytes();art=Path(receipt(apps[0])['path']);artbytes=art.read_bytes()
  for label,mutate in [('malformed',lambda:b'{'),('unknown',lambda:json.dumps(dict(json.loads(saved),extra=1)).encode()),('wrong-key',lambda:json.dumps(dict(json.loads(saved),key='0'*64)).encode()),('wrong-version',lambda:json.dumps(dict(json.loads(saved),format=99)).encode()),('wrong-path',lambda:json.dumps(dict(json.loads(saved),artifact='/bin/true')).encode())]:
   data=mutate();ready.write_bytes(data);before=len(events());bad=finish(start(apps[1],{'RNX_FORBID_BUILD':'1'}),False);assert ready.read_bytes()==data and builds(events()[before:])==0;rows['ready-'+label]=bad;ready.write_bytes(saved)
  art.write_bytes(artbytes[:-1]+bytes([artbytes[-1]^1]));rows['corrupt-artifact']=finish(start(apps[1],{'RNX_FORBID_BUILD':'1'}),False);assert ready.read_bytes()==saved;art.write_bytes(artbytes)
  # Root spelling allowed; managed symlink, FIFO and writable directory refused.
  rows['relative-root']=finish(start(apps[1],{'RNX_PROJECT_CACHE':'.'}),False)
  link=root/'cache-link';link.symlink_to(cache,target_is_directory=True);rows['root-symlink']=finish(start(apps[1],{'RNX_PROJECT_CACHE':str(link),'RNX_FORBID_BUILD':'1'}))
  ready.unlink();ready.symlink_to(root/'identity.json');rows['ready-symlink']=finish(start(apps[1]),False);ready.unlink();os.mkfifo(ready);rows['ready-fifo']=finish(start(apps[1]),False);ready.unlink();ready.write_bytes(saved)
  entry.chmod(0o777);rows['writable-entry']=finish(start(apps[1]),False);entry.chmod(0o700)
  backup=entry.with_name(key+'-saved');entry.rename(backup);entry.symlink_to(backup,target_is_directory=True);rows['entry-symlink']=finish(start(apps[1]),False);entry.unlink();backup.rename(entry)
  lockfile=cache/'locks'/f'{key}.lock';original_lock=lockfile.read_bytes();lockfile.unlink();lockfile.symlink_to(root/'identity.json');rows['lock-symlink']=finish(start(apps[1]),False);lockfile.unlink();os.mkfifo(lockfile);rows['lock-fifo']=finish(start(apps[1]),False);lockfile.unlink();lockfile.write_bytes(original_lock)
  art.unlink();art.symlink_to(root/'identity.json');rows['artifact-symlink']=finish(start(apps[1]),False);art.unlink();art.write_bytes(artbytes);art.chmod(0o700)
  # Missing cache checked through production readiness API, no compiler invocation.
  shutil.rmtree(entry);before=len(events());p=call([T,'ready-check',ip],dict(env,RNX_FORBID_BUILD='1'),ok=False);assert p.returncode!=0 and len(events())==before;rows['missing-entry']={'status':p.returncode,'stderr':p.stderr}
  # Preserve reconstructible fixture inputs and process outcomes, never build trees.
  shutil.copytree(n,O/'native',dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git'))
  for f in [ip,root/'context.json',root/'metadata.json']:shutil.copyfile(f,O/f.name)
  shutil.copyfile(stage/'Cargo.lock',O/'Cargo.lock');shutil.copyfile(stage/'Cargo.toml',O/'Cargo.toml')
  assert all(not Path('/proc',str(v['child_pid'])).exists() for k,v in rows.items() if k.startswith('builder-'))
  for trace in (O/'compiler-traces').glob('*.jsonl'):
   if str(root) not in trace.read_text():trace.unlink()
  (O/'results.json').write_text(json.dumps(rows,indent=2)+'\n');(O/'conditions.json').write_text(json.dumps({'rnx_head':call(['git','-C',R,'rev-parse','HEAD'],env).stdout.strip(),'probe_sha256':sha(T.read_bytes()),'rustc':rustcv,'cargo':cargov,'source_patch':'source.patch','scope':'production entry module, isolated driver; fixture project receipts (product receipt migration is gate 4); SIGINT/SIGTERM builder process-group contract; hard-killed waiter'},indent=2)+'\n')
finally:
 for p,out,err in children:
  if p.poll() is None:p.send_signal(signal.SIGTERM);p.wait(timeout=10)
  out.close();err.close()
 os.umask(oldmask)
print('PASS',len(rows),'publication/concurrency cases',flush=True)
