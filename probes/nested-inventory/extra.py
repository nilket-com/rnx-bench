"""Additional topology checks and the real constant zero-to-three roster."""
from pathlib import Path
import json,os,subprocess as sp,shutil,collections
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target/extra';O=B/'results/nested-inventory-0065';T=H/'target/tool/tools/project/target/release/nested-probe'
assert not W.exists();W.mkdir();E={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','RNX_','NESTED_'))};home=W/'home';home.mkdir();E.update(HOME=str(home),XDG_CONFIG_HOME=str(home));rows=[]
def git(p,*args):return sp.check_output(['git','-C',p,*args],env=E,stderr=sp.PIPE)
def fixture(name):
 p=W/name;(p/'a/sub').mkdir(parents=True);git(p,'init','-q');(p/'base').write_text('root');(p/'a/one').write_text('adapter');(p/'a/sub/two').write_text('nested');git(p,'add','.');git(p,'-c','user.name=Fixture','-c','user.email=f@invalid','-c','commit.gpgsign=false','commit','-qm','fixture');return p
def pair(name,roots,env=None):
 data=[]
 for candidate in [False,True]:
  q=W/'config.json';q.write_text(json.dumps(dict(roots=list(map(str,roots)),candidate=candidate,entries=100000,bytes=512*1024*1024)))
  p=sp.run([T,q],env=E|(env or {}),capture_output=True,text=True,timeout=60);assert p.returncode==0,p.stderr;data.append(json.loads(p.stdout))
 assert data[0]['answer']==data[1]['answer'],(name,data)
 assert data[0]['remaining_bytes']==data[1]['remaining_bytes']
 rows.append(dict(case=name,oracle=data[0],candidate=data[1]));(O/'extra.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS',name,flush=True);return data
p=fixture('linked');link=W/'worktree';git(p,'worktree','add','-q','--detach',str(link));r=pair('linked-worktree',[link,link/'a']);assert sum('git' in x for x in r[1]['events'])==6
p=fixture('separate');git(p/'a','init','-q','--separate-git-dir',str(W/'separate-admin'));git(p/'a','add','.');r=pair('intervening-git-file',[p,p/'a']);assert sum('git' in x for x in r[1]['events'])==6
p=fixture('ignored-nested');(p/'.gitignore').write_text('a/ignored/\n');git(p,'add','.gitignore');(p/'a/ignored').mkdir();git(p/'a/ignored','init','-q');r=pair('ignored-nested-repository',[p,p/'a']);assert sum('git' in x for x in r[1]['events'])==6
p=fixture('root-symlink');alias=W/'alias';alias.symlink_to(p/'a',target_is_directory=True);pair('symlink-root',[p,alias])
p=fixture('fifo');(p/'a/one').unlink();os.mkfifo(p/'a/one');pair('tracked-fifo',[p,p/'a'])
p=fixture('nonunicode');f=os.fsencode(p/'a')+b'/\xff';open(f,'wb').write(b'x');git(p,'add','.');pair('non-Unicode',[p,p/'a'])
p=fixture('backslash');(p/'a/a\\b').write_text('x');git(p,'add','.');pair('backslash-name',[p,p/'a'])
p=fixture('new\nline');pair('newline-root-fallback',[p,p/'a'])
p=fixture('submodule-owner');ext=fixture('submodule-source');git(p,'-c','protocol.file.allow=always','submodule','add','-q',str(ext), 'module');pair('submodule-root',[p/'module',p/'module/a'])
p=fixture('discovery-bound');(p/'.gitignore').write_text('a/ignored/\n');git(p,'add','.gitignore');(p/'a/ignored').mkdir()
for n in range(4097):(p/'a/ignored'/str(n)).touch()
r=pair('discovery-limit-fallback',[p,p/'a']);assert sum('git' in x for x in r[1]['events'])==6
p=fixture('nested-prefix');r=pair('three-level',[p,p/'a',p/'a/sub']);assert sum('git' in x for x in r[1]['events'])==3
# Shared runtime from the accepted measurement: the complete copied third adapter
# stays in the runtime at all declaration counts.
p=B/'probes/native-inventory/target/s';assert p.is_dir()
for n in range(4):
 roots=[p]+[p/'adapters'/name for name in ['polars','postgres','pgcopy'][:n]];r=pair('real-roster-'+str(n),roots)
 assert 'Ok' in r[0]['answer'],r
 reads=collections.Counter(x['read'] for x in r[1]['events'] if 'read' in x);assert max(reads.values())==1
 assert sum('git' in x for x in r[1]['events'])==3
 assert sum('git' in x for x in r[0]['events'])==3*(n+1)
 for root in roots:assert git(p,'rev-parse','--show-toplevel')==git(root,'rev-parse','--show-toplevel')

# Two calls in one process retain no file/Git observations between them.
q=W/'repeat.json';q.write_text(json.dumps(dict(roots=[str(p),str(p/'adapters/polars')],candidate=True,repeat=True,entries=100000,bytes=512*1024*1024)))
r=json.loads(sp.check_output([T,q],env=E));assert r['answer']==r['repeated'];counts=collections.Counter(x['read'] for x in r['events'] if 'read' in x);assert set(counts.values())=={2};assert sum('git' in x for x in r['events'])==6
rows.append(dict(case='same-process-second-inventory',result=r));(O/'extra.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS same-process-second-inventory',flush=True)
