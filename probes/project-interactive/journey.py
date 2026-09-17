from common import *
import tempfile,json,hashlib
r=json.loads((P/'.rnx/receipt.json').read_text());A=P/'.rnx/artifacts'/r['executable_sha256'];base=[T,'session','--manifest',P/'rnx.toml'];direct=[A,'repl'];results={}
with tempfile.TemporaryDirectory(prefix='rnx-0060-journey-') as tmp:
 cwd=pathlib.Path(tmp);env=dict(ENV,RNX_CONFIG=str(cwd/'absent'),RNX_HISTORY=str(cwd/'history'))
 for kind,cmd in [('project',base+['--no-splash','--color=never']),('direct',[A,'--no-splash','--color=never','repl'])]:
  work=cwd/kind;work.mkdir();t=Terminal(cmd,work,env)
  try:
   t.read()
   # A second process can acquire the same advisory lock while the prompt lives.
   if kind=='project':
    with (P/'.rnx/command.lock').open('rb') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
   t.send('fs::write_new("tiny.csv", "category,value\\na,1\\na,2\\n🦀,3\\n🦀,4\\nmissing,\\n").unwrap();')
   assert (work/'tiny.csv').exists()
   t.send('let frame = polars::read_csv("tiny.csv", [("category","string"),("value","i64")]).unwrap();')
   t.send('let grouped = frame.lazy().filter(polars::col("value").gt(polars::lit(1).unwrap())).group_by([polars::col("category")]).unwrap();')
   t.send('let plan = grouped.agg([polars::col("value").sum().alias("total")]).unwrap().sort(["category"]).unwrap();')
   t.send('let result = plan.collect().unwrap();')
   out=t.send('println!("{}", result.preview().unwrap());');assert '"a" | 2' in out and '"🦀" | 7' in out,out
   out=t.send('frame.lazy().sort(["missing"]).unwrap().collect()');assert 'Err' in out and 'missing' in out,out
   out=t.send('println!("{}", frame.preview().unwrap());');assert '5 rows' in out,out
   t.send('result.write_parquet_new("tiny.parquet").unwrap();')
   out=t.send('assert!(polars::read_parquet("tiny.parquet").unwrap().preview().unwrap() == result.preview().unwrap());');assert 'error' not in out.lower(),out
   out=t.send('mod dep;');assert 'modules' in out.lower(),out
   t.send(':reset');out=t.send('frame');assert 'No local variable' in out,out
   out=t.send('polars::lit(1).is_ok()');assert 'true' in out,out
   # Real terminal control byte; no OS signal masquerading as a keypress.
   os.write(t.master,b'\x03');t.read();out=t.send('6 * 7');assert '42' in out,out
   os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
   assert not (work/'entry-ran').exists()
  finally:
   (O/(kind+'-pty.bin')).write_bytes(t.log);(O/(kind+'-pty.txt')).write_text('\n'.join(x.rstrip() for x in text(t.log).splitlines())+'\n');t.close()
  results[kind+'_journey']=True
 # Byte comparisons in non-terminal eval, including the existing exit contract.
 for i,src in enumerate(['42','"🦀"','', '-42','let x=2;\nx+1','unknown_name','polars::read_csv("absent.csv", [("v","i64")])','process::exit(3)','mod dep;']):
  p=call([T,'eval','--manifest',P/'rnx.toml','--color=never','--',src],cwd,env=env);d=call([A,'--color=never','eval',src],cwd,env=env)
  assert (p.returncode,p.stdout,p.stderr)==(d.returncode,d.stdout,d.stderr),(src,p,d)
  (O/f'eval-{i}.json').write_text(json.dumps({'source':src,'status':p.returncode,'stdout':p.stdout,'stderr':p.stderr},ensure_ascii=False,indent=2)+'\n')
 results['direct_eval_byte_comparison']=True
 # Non-Unicode source reaches the engine's own argument refusal unchanged.
 for cmd in [[os.fsencode(T),b'eval',b'--manifest',os.fsencode(P/'rnx.toml'),b'--',b'\xff'],[os.fsencode(A),b'eval',b'\xff']]:
  p=subprocess.run(cmd,cwd=cwd,env=env,capture_output=True);assert p.returncode==2
  if cmd[0]==os.fsencode(T):ref=(p.returncode,p.stdout,p.stderr)
  else:assert ref==(p.returncode,p.stdout,p.stderr)
 # Missing/broken derived map cannot block either mode, and isn't repaired.
 maps=P/'.rnx/maps';assert not maps.exists() or not list(maps.iterdir())
 maps.mkdir(exist_ok=True);mapbytes=json.dumps(json.loads((P/'rnx.lock').read_text())['sources'],ensure_ascii=False,separators=(',',':')).encode()
 broken=maps/(hashlib.sha256(mapbytes).hexdigest()+'.json');broken.write_bytes(b'{bad');st=broken.stat()
 for cmd in [[T,'eval','--manifest',P/'rnx.toml','--','42'],base+['--no-splash','--color=never']]:
  p=call(cmd,cwd,stdin='42\n:q\n',env=env);assert p.returncode==0 and '42' in p.stdout,p.stderr
 assert list(maps.iterdir())==[broken] and broken.read_bytes()==b'{bad' and broken.stat().st_mtime_ns==st.st_mtime_ns
 broken.unlink();maps.rmdir()
 dep=P/'dep/mod.rn';raw=dep.read_bytes();st=dep.stat()
 try:
  dep.write_bytes(raw.replace(b'42',b'43'));os.utime(dep,ns=(st.st_atime_ns,st.st_mtime_ns))
  for cmd in [[T,'eval','--manifest',P/'rnx.toml','--','42'],base]:
   p=call(cmd,cwd,stdin=':q\n',env=env);assert p.returncode!=0 and not p.stdout and 'changed' in p.stderr,p
 finally:dep.write_bytes(raw)
 results['mapped_scope_entry_and_cwd']=True
 # Configuration is session-only, and piped sessions retain native bindings.
 config=cwd/'config.rn';config.write_text('polars::col("v"); #{splash:false}')
 cfg=dict(env,RNX_CONFIG=str(config))
 p=call([T,'eval','--manifest',P/'rnx.toml','--','42'],cwd,env=cfg);assert not p.stderr and p.returncode==0
 p=call(base+['--no-splash','--color=never'],cwd,stdin='let f=polars::lit(1).unwrap();\nf\n:reset\npolars::lit(2).is_ok()\n:q\n',env=cfg);assert p.returncode==0 and 'config' in p.stderr and 'polars' in p.stderr and 'true' in p.stdout,(p.stdout,p.stderr)
 for kind,cmd in [('project',base+['--color=always']),('direct',[A,'--color=always','repl'])]:
  t=Terminal(cmd,cwd,env)
  try:
   out=t.read();assert b'\x1b[' in t.log
   os.write(t.master,b'\x04');t.read(False);assert t.p.wait(timeout=5)==0
  finally:(O/(kind+'-eof.bin')).write_bytes(t.log);t.close()
 assert not (cwd/'entry-ran').exists();results['settings_piped_and_terminal_eof']=True
(O/'journey.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS',results)
