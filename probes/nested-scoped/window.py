"""Record the once-per-parent administration observation window between children."""
from pathlib import Path
import json,os,subprocess as sp,time
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target/window';O=B/'results/nested-scoped-0065';T=B.parent/'rnx/tools/project/target/debug/rnx-project-assembly-probe'
assert not W.exists();W.mkdir();E={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','RNX_','NESTED_'))};E.update(HOME=str(W),XDG_CONFIG_HOME=str(W));rows=[]
for candidate in [False,True]:
 p=W/str(candidate);(p/'a').mkdir(parents=True);(p/'b').mkdir();(p/'base').write_text('root');(p/'a/one').write_text('one');(p/'b/two').write_text('two')
 def git(*args):sp.run(['git','-C',p,*args],env=E,check=True,stdout=sp.DEVNULL,stderr=sp.PIPE)
 git('init','-q');git('add','.')
 q=W/'config.json';q.write_text(json.dumps(dict(roots=list(map(str,[p,p/'a',p/'b'])),candidate=candidate,entries=100000,bytes=512*1024*1024)))
 marker=W/f'pause-{candidate}';proc=sp.Popen([T,'nested-inventory',q],env=E|{'NESTED_PAUSE_ROOT':str(p/'a'),'NESTED_PAUSE':str(marker)},stdout=sp.PIPE,stderr=sp.PIPE,text=True)
 try:
  for _ in range(1000):
   if marker.exists():break
   assert proc.poll() is None;time.sleep(.005)
  else:raise AssertionError('no pause')
  (p/'b/new').write_text('new tracked input');git('add','b/new');marker.with_suffix('.release').write_text('release')
  out,err=proc.communicate(timeout=20);assert proc.returncode==0,err
 finally:
  if proc.poll() is None:proc.kill();proc.wait()
 first=json.loads(out);nxt=json.loads(sp.check_output([T,'nested-inventory',q],env=E))
 assert 'Ok' in first['answer'] and 'Ok' in nxt['answer']
 changed=first['answer']['Ok'][2]['blake3']!=nxt['answer']['Ok'][2]['blake3'];assert changed==candidate
 rows.append(dict(candidate=candidate,first=first,next=nxt))
(O/'between-children.json').write_text(json.dumps(dict(case='tracked addition after first shared administration recheck',observations=rows,qualification='candidate sees addition next invocation; independent second child sees it in this invocation; neither is an atomic snapshot'),indent=2)+'\n');print('PASS explicit between-child observation window')
