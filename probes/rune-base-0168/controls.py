"""Corpus fixed before deciding measurement; subprocess limits isolate robustness failures."""
import json,pathlib,resource,subprocess,os,signal
P=pathlib.Path(__file__).resolve().parent;O=P.parents[1]/'results/rune-base-0168';O.mkdir(exist_ok=True)
CORPUS={
'int-boundaries':('pub fn main(_args) { println!("{}",9223372036854775807); println!("{}",-9223372036854775807-1); }','9223372036854775807\n-9223372036854775808\n','run'),
'floats':('pub fn main(_args) { println!("{}",0.25+0.5); println!("{}",1.5*2.0); }','0.75\n3.0\n','run'),
'unicode':('pub fn main(_args) { let s="a🦀é"; println!("{}",s.len()); println!("{}",s); }','7\na🦀é\n','run'),
'vec-alias':('pub fn main(_args) { let a=[1]; let b=a; b.push(2); println!("{}",a.len()); }','2\n','run'),
'object-alias':('pub fn main(_args) { let a=#{n:1}; let b=a; b.n=2; println!("{}",a.n); }','2\n','run'),
'closure':('pub fn main(_args) { let f=|x| x+1; println!("{}",f(41)); }','42\n','run'),
'iterator-trait':('pub fn main(_args) { let n=[1,2,3].iter().map(|x|x*2).sum::<i64>(); println!("{}",n); }','12\n','run'),
'sum-untyped':('pub fn main(_args) { println!("{}",[1,2,3].iter().sum()); }',None,'run'),
'async':('async fn plus(x) { x+1 } pub async fn main(_args) { println!("{}",plus(41).await); }','42\n','async'),
'overflow':('pub fn main(_args) { let n=9223372036854775807; println!("{}",n+1); }',None,'run'),
'divide-zero':('pub fn main(_args) { let n=0; println!("{}",1/n); }',None,'run'),
'undefined':('pub fn main(_args) { absent }',None,'run'),
'budget':('pub fn main(_args) { loop {} }',None,'run')}
def limit():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(5,6))
def invoke(exe,mode,path,budget='1000000000'):
 cmd=[str(exe),mode,str(path),budget]
 p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,preexec_fn=limit)
 try:stdout,stderr=p.communicate(timeout=10)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGKILL);stdout,stderr=p.communicate();return dict(command=cmd,status=p.returncode,stdout=stdout.decode(errors='replace'),stderr=stderr.decode(errors='replace'),outcome='timeout')
 err=stderr.decode(errors='replace')
 outcome='correct' if p.returncode==0 else ('signal:'+str(-p.returncode) if p.returncode<0 else ('compile-error' if err.startswith(('compile:','source:','insert:')) else 'vm-error' if err.startswith(('vm:','execute:')) else 'other-error'))
 return dict(command=cmd,status=p.returncode,stdout=stdout.decode(errors='replace'),stderr=err,outcome=outcome)
rows=[]
for name,(source,expected,mode) in CORPUS.items():
 path=P/'fixtures'/(name+'.rn');path.write_text(source+'\n')
 for base in ['old','new']:
  r=invoke(P/base/'target/release'/'primary',mode,path,'100' if name=='budget' else '1000000000');r.update(base=base,name=name,expected=expected)
  r['passed']=r['outcome']=='correct' and r['stdout']==expected if expected is not None else r['outcome'] in ('vm-error','compile-error') and not r['stdout']
  if expected is None:
   classes={'sum-untyped':'MissingInstanceFunction','overflow':'Overflow','divide-zero':'DivideByZero','undefined':'MissingLocal','budget':'Limited'}
   r['semantic_error']=classes[name];r['passed']=r['passed'] and classes[name] in r['stderr']
  rows.append(r)
(O/'correctness.json').write_text(json.dumps(rows,indent=2)+'\n')
assert all(r['passed'] for r in rows),[r for r in rows if not r['passed']]
# Robustness records outcomes, never manufactures successful parity from a crash.
robust=[]
for kind,depths in [('recursion',[10000,100000,1000000]),('expression',[100,1000,10000]),('literal',[100,1000,10000])]:
 for depth in depths:
  if kind=='recursion':source=f'fn descend(n) {{ if n==0 {{ return 0; }} descend(n-1)+1 }} pub fn main(_args) {{ println!("{{}}",descend({depth})); }}';expected=str(depth)+'\n'
  elif kind=='expression':source='pub fn main(_args) { println!("{}",'+'('*depth+'1'+')'*depth+'); }';expected='1\n'
  else:source='pub fn main(_args) { let v='+'['*depth+'1'+']'*depth+'; println!("{}",v.len()); }';expected='1\n'
  path=P/'fixtures'/(kind+'-'+str(depth)+'.rn');path.write_text(source+'\n')
  for base in ['old','new']:
   r=invoke(P/base/'target/release'/'primary','run',path);r.update(base=base,kind=kind,depth=depth,expected=expected,source_bytes=path.stat().st_size)
   if r['outcome']=='correct' and r['stdout']!=expected:r['outcome']='wrong-answer'
   robust.append(r);print(base,kind,depth,r['outcome'],flush=True)
(O/'robustness.json').write_text(json.dumps(dict(limits=dict(address_space_bytes=2*1024**3,cpu_soft_s=5,cpu_hard_s=6,wall_s=10,core_bytes=0),rows=robust),indent=2)+'\n')
