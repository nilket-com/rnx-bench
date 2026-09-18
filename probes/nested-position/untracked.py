"""A non-ignored nested repository with no parent-tracked files refuses on both roots."""
from pathlib import Path
import json,os,subprocess as sp
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target/untracked';O=B/'results/nested-position-0065';T=B.parent/'rnx/tools/project/target/debug/rnx-project-assembly-probe';assert not W.exists();(W/'a').mkdir(parents=True)
E={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','RNX_','NESTED_'))};E.update(HOME=str(W),XDG_CONFIG_HOME=str(W))
def git(p,*args):sp.run(['git','-C',p,*args],env=E,check=True,stdout=sp.DEVNULL,stderr=sp.PIPE)
git(W,'init','-q');(W/'base').write_text('runtime');(W/'a/one').write_text('adapter');git(W,'add','.');nested=W/'a/new';nested.mkdir();git(nested,'init','-q');(nested/'file').write_text('nested repo');git(nested,'add','.');git(nested,'-c','user.name=Fixture','-c','user.email=f@invalid','-c','commit.gpgsign=false','commit','-qm','fixture')
results=[]
for roots in [[W,W/'a'],[W/'a']]:
 data=[]
 for candidate in [False,True]:
  q=H/'target/untracked-config.json';q.write_text(json.dumps(dict(roots=list(map(str,roots)),candidate=candidate,entries=100000,bytes=512*1024*1024)));p=sp.run([T,'nested-inventory',q],env=E,capture_output=True,text=True,timeout=20);assert p.returncode==0,p.stderr;data.append(json.loads(p.stdout))
 assert data[0]['answer']==data[1]['answer'] and 'untracked' in data[1]['answer']['Err'];results.append(dict(roots=list(map(str,roots)),oracle=data[0],candidate=data[1]))
(O/'untracked-repository.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS untracked nested repository refuses parent and independent child')
