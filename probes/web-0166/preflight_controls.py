"""Deliberately copy before four preflights: the real-VM allocation gate must fail.
Run with exclusive ownership of the specified checkout; the source is restored in finally.
"""
import pathlib,subprocess,sys
repo=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
p=repo/'src/web.rs';original=p.read_text()
mutations=[
 ('escape-expansion','fn escape_html_checked(s: &str) -> Result<String, String> {','\n\tstd::hint::black_box(s.repeat(5));'),
 ('form-component','fn form(body: Value) -> Result<Value, String> {','\n\twith_bytes(&body, |b| { std::hint::black_box(b.to_vec()); Ok(()) })?;'),
 ('response-body',') -> Result<Value, String> {\n\twith_bytes(&body, |b| status(status_code, b.len()))?;','\n\twith_bytes(&body, |b| { std::hint::black_box(b.to_vec()); Ok(()) })?;'),
 ('header-vector','\tbounded(list.len(), HEADERS, "response header values")?;','\n\tstd::hint::black_box(list.iter().cloned().collect::<Vec<_>>());'),
]
try:
 for name,anchor,insert in mutations:
  assert original.count(anchor)==1,(name,original.count(anchor))
  if name=='response-body':
   changed=original.replace(anchor,anchor.split('\n')[0]+insert+'\n\twith_bytes(&body, |b| status(status_code, b.len()))?;')
  elif name=='header-vector':changed=original.replace(anchor,insert+'\n'+anchor)
  else:changed=original.replace(anchor,anchor+insert)
  p.write_text(changed)
  r=subprocess.run(['cargo','test','--offline','--features','test-support','--test','web_alloc','--','--nocapture'],cwd=repo,capture_output=True,text=True)
  log=r.stdout+r.stderr;(out/(name+'.txt')).write_text(log)
  assert r.returncode!=0 and 'bytes allocated' in log,(name,r.returncode,log[-2000:])
  print(name+': copying before preflight fails the real-VM allocation assertion',flush=True)
finally:p.write_text(original)
r=subprocess.run(['cargo','test','--offline','--features','test-support','--test','web_alloc','--','--nocapture'],cwd=repo,capture_output=True,text=True)
(out/'restored.txt').write_text(r.stdout+r.stderr);assert r.returncode==0
print('restored source: all five refusals pass below 256 KiB',flush=True)
