from pathlib import Path
import os,subprocess as sp,json,shutil,time
H=Path('/home/me/work/rnx-bench/probes/nested-product');B=Path('/home/me/work/rnx-bench');W=H/'target/matrix';O=Path('/home/me/work/rnx-bench/results/nested-product-0065');T=Path('/home/me/work/rnx-bench/probes/nested-product/target/nested-probe')
assert not W.exists();W.mkdir();E={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','RNX_','NESTED_'))};E.update(GIT_CONFIG_NOSYSTEM='1')
# Remove even harmless Git routing settings for eligible controls; isolated HOME
# prevents machine configuration from deciding the fixture topology.
E.pop('GIT_CONFIG_NOSYSTEM');home=W/'home';home.mkdir();E['HOME']=str(home);E['XDG_CONFIG_HOME']=str(home)
rows=[]
def git(p,*args):return sp.check_output(['git','-C',p,*args],env=E,stderr=sp.PIPE)
def fixture(name):
 p=W/name;p.mkdir();git(p,'init','-q');git(p,'config','user.email','fixture@example.invalid');git(p,'config','user.name','Fixture')
 (p/'a/sub').mkdir(parents=True);(p/'a/one').write_text('abcd');(p/'a/sub/two').write_text('efgh');(p/'base').write_text('runtime');(p/'.gitignore').write_text('ignored/\nignored-file\n')
 git(p,'add','.');git(p,'commit','-qm','fixture');return p

def run(roots,candidate,env=None,entries=100000,bytes=512*1024*1024,pause=None):
 cfg=W/'config.json';cfg.write_text(json.dumps(dict(roots=list(map(str,roots)),candidate=candidate,entries=entries,bytes=bytes)))
 e=E| (env or {})
 if pause:
  marker=W/'pause';marker.unlink(missing_ok=True);marker.with_suffix('.release').unlink(missing_ok=True);e.update(NESTED_PAUSE_ROOT=str(roots[0]),NESTED_PAUSE=str(marker))
  proc=sp.Popen([T,cfg],env=e,stdout=sp.PIPE,stderr=sp.PIPE,text=True)
  for _ in range(1000):
   if marker.exists():break
   assert proc.poll() is None,proc.communicate();time.sleep(.005)
  else:raise AssertionError('no pause')
  pause();marker.with_suffix('.release').write_text('release');out,err=proc.communicate(timeout=20);assert proc.returncode==0,err
 else:
  proc=sp.run([T,cfg],env=e,capture_output=True,text=True,timeout=20);assert proc.returncode==0,proc.stderr;out=proc.stdout
 return json.loads(out)
def pair(name,p,extra=None,**kw):
 roots=[p,p/'a'] if extra is None else extra
 a=run(roots,False,**kw);b=run(roots,True,**kw)
 assert a['answer']==b['answer'],(name,a,b)
 assert a['remaining_bytes']==b['remaining_bytes'],(name,'allowance',a,b)
 def counts(r):return dict(git=sum('git' in x for x in r['events']),reads=sum('read' in x for x in r['events']),reused=sum('reuse' in x for x in r['events']))
 row=dict(case=name,oracle=a,candidate=b,counts=dict(oracle=counts(a),candidate=counts(b)))
 rows.append(row);print('PASS',name,row['counts'],flush=True);(O/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n');return row
p=fixture('basic');x=pair('quiescent',p);assert x['counts']['candidate']==dict(git=3,reads=4,reused=1);assert x['counts']['oracle']==dict(git=6,reads=6,reused=0)
# Independently scoped Git proof recorded, including top and exact file paths.
assert git(p,'rev-parse','--show-toplevel')==git(p/'a','rev-parse','--show-toplevel')
(p/'a/ignored').mkdir();(p/'a/ignored/cache').write_text('ignored');pair('ignored',p)
(p/'a/untracked').write_text('extra');pair('untracked-child',p);(p/'a/untracked').unlink()
(p/'a/new').write_text('added');git(p,'add','a/new');pair('staged-addition',p)
git(p,'rm','-fq','a/new');pair('staged-deletion',p)
(p/'a/one').chmod(0o755);pair('working-executable',p)
git(p,'update-index','--chmod=+x','a/one');pair('staged-executable',p)
(p/'a/one').unlink();pair('missing-tracked',p)
p=fixture('empty');(p/'empty').mkdir();pair('empty-root',p,extra=[p,p/'empty'])
p=fixture('nested-root');git(p/'a','init','-q');git(p/'a','add','.');x=pair('nested-repository-at-root',p);assert x['counts']['candidate']['git']==6 and x['counts']['candidate']['reads']==6
p=fixture('nested-inside');git(p/'a/sub','init','-q');git(p/'a/sub','add','.');x=pair('nested-repository-inside-adapter',p);assert x['counts']['candidate']['git']==6
p=fixture('external');q=fixture('outside');x=pair('external-repository',p,extra=[p,q/'a']);assert x['counts']['candidate']['git']==6
p=fixture('symlink');(p/'a/one').unlink();(p/'a/one').symlink_to('../base');pair('working-symlink',p)
git(p,'add','a/one');pair('staged-symlink',p)
p=fixture('component');shutil.move(p/'a/sub',p/'moved');(p/'a/sub').symlink_to('../moved');git(p,'add','moved');pair('symlinked-component',p)
p=fixture('conflict');blob=git(p,'hash-object','a/one').decode().strip();sp.run(['git','-C',p,'update-index','--index-info'],input=f'100644 {blob} 1\ta/one\n100644 {blob} 2\ta/one\n'.encode(),env=E,check=True);pair('unmerged',p)
p=fixture('gitlink');blob=git(p,'rev-parse','HEAD').decode().strip();git(p,'rm','-r','--cached','-q','a');git(p,'update-index','--add','--cacheinfo',f'160000,{blob},a');pair('gitlink-at-child',p)
p=fixture('env');
for var,val in [('GIT_CONFIG_COUNT','0'),('GIT_DIR',str(p/'.git')),('GIT_WORK_TREE',str(p)),('GIT_INDEX_FILE',str(p/'.git/index')),('GIT_CEILING_DIRECTORIES',str(W))]:
 x=pair(var,p,env={var:val});assert x['counts']['candidate']==x['counts']['oracle']
p=fixture('limits');total=sum(f.stat().st_size for f in [p/'.gitignore',p/'base',p/'a/one',p/'a/sub/two'])+8
for n in [3,4,5,6]:pair(f'entry-limit-{n}',p,entries=n)
for n in [total-9,total-1,total,total+1]:pair(f'byte-limit-{n}',p,bytes=n)
# Every invocation reads content. Restoring mtime does not hide a pre-launch edit.
p=fixture('content');before=pair('before-edit',p);f=p/'a/one';m=f.stat();f.write_text('wxyz');os.utime(f,ns=(m.st_atime_ns,m.st_mtime_ns));after=pair('restored-mtime-before-launch',p);assert before['candidate']['answer']!=after['candidate']['answer']
# Explicitly measured observation-window divergence, using fresh trees per side.
for kind in ['mtime','index','boundary','restored']:
 observed=[]
 for mode in [False,True]:
  p=fixture(f'timed-{kind}-{mode}');f=p/'a/one';m=f.stat()
  def mutate():
   if kind in ['mtime','restored']:
    f.write_text('wxyz')
    if kind=='restored':os.utime(f,ns=(m.st_atime_ns,m.st_mtime_ns))
   elif kind=='index':git(p,'update-index','--chmod=+x','a/one')
   else:git(p/'a','init','-q');git(p/'a','add','.')
  first=run([p,p/'a'],mode,pause=mutate);second=run([p,p/'a'],mode);observed.append(dict(candidate=mode,first=first,next=second))
 if kind=='restored':
  assert 'Ok' in observed[0]['first']['answer'] and 'Ok' in observed[1]['first']['answer']
  for row in observed:
   trees=row['first']['answer']['Ok'];nxt=row['next']['answer']['Ok'];assert trees[0]['blake3']!=nxt[0]['blake3']
   assert (trees[1]['blake3']==nxt[1]['blake3']) != row['candidate']
 else:assert 'Err' in observed[1]['first']['answer'],(kind,observed)
 rows.append(dict(case='timed-'+kind,observations=observed));(O/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS timed',kind,flush=True)
