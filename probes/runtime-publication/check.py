"""0064 gate two: real installer, tiny tracked layouts, explicit faults and ownership."""
from pathlib import Path
import os,sys,subprocess as sp,json,shutil,time,signal,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/runtime-publication-0064'
if W.exists():raise SystemExit('fresh target required')
W.mkdir();O.mkdir(exist_ok=True);original_tool=Path(os.environ.get('RNX_INSTALL_TOOL',R/'tools/project/target/debug/rnx-project')).resolve();T=W/'rnx-project';shutil.copy2(original_tool,T)
E={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','GIT_'))}
E.update(XDG_DATA_HOME=str(W/'data'),RNX_PROJECT_CACHE=str(W/'cache'),XDG_STATE_HOME=str(W/'state'),GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1')
STORE=W/'data/rnx/runtimes';rows=[]
def save(): (O/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n')
def record(name,**detail):rows.append(dict(name=name,**detail));save();print('PASS',name,flush=True)
def run(args,env=E,ok=True,timeout=30):
 p=sp.run([str(T),'runtime',*map(str,args)],env=env,capture_output=True,text=True,timeout=timeout)
 if ok:assert p.returncode==0,(args,p.stdout,p.stderr)
 else:assert p.returncode!=0,(args,p.stdout,p.stderr)
 return p

def git(p,*args,env=E):return sp.check_output(['git','-C',str(p),*map(str,args)],env=env,stderr=sp.PIPE)
def fixture(name):
 p=W/name;p.mkdir();git(p,'init','-q','--template=')
 (p/'src').mkdir();(p/'Cargo.toml').write_text('[package]\nname="rnx"\nversion="0.0.0"\nedition="2024"\n[workspace]\n');(p/'src/main.rs').write_text('fn main() {}\n');(p/'src/lib.rs').write_text('// runtime\n')
 for a,pkg in [('polars','rnx-polars'),('postgres','rnx-postgres')]:
  d=p/'adapters'/a;(d/'src').mkdir(parents=True);(d/'src/lib.rs').write_text('// adapter\n');(d/'Cargo.toml').write_text('[package]\nname='+json.dumps(pkg)+'\nversion="0.0.0"\n[workspace]\n[dependencies]\nrnx={path="../.."}\n')
 (p/'.gitignore').write_text('ignored/\n');git(p,'add','.');git(p,'-c','user.name=Fixture','-c','user.email=fixture@invalid','-c','commit.gpgsign=false','commit','-qm','fixture');return p

def installation(result):return result.stdout.split('runtime ',1)[1].splitlines()[0]
def current():return (STORE/'current.json').read_bytes()
def tree(path):
 return {str(p.relative_to(path)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_ino,p.stat().st_mtime_ns,p.stat().st_mode) for p in path.rglob('*') if p.is_file()}
def unchanged(old):assert current()==old;assert not list(STORE.glob('.stage-*'));assert not list(STORE.glob('.current-*'))
A=fixture('source-a');original=tree(A);aid=installation(run(['install','--from',A]));assert tree(A)==original
old=current();entry=STORE/'entries'/aid;baseline=tree(entry);assert run(['show']).stdout.find(aid)>=0
assert installation(run(['install','--from',A]))==aid;assert tree(entry)==baseline;assert tree(A)==original
record('install and same-ID validate/reselect',id=aid,no_source_write=True,entry_byte_inode_mtime_identity=True)
Bsrc=fixture('source-b');(Bsrc/'src/lib.rs').write_text('// dirty second snapshot\n');bid=installation(run(['install','--from',Bsrc]));bentry=STORE/'entries'/bid;doc=json.loads((bentry/'installation.json').read_text());assert doc['dirty_tracked'];assert doc['source_commit'];run(['select',aid]);assert current()==old
record('dirty snapshot, retained installations and explicit selection',id=bid)
# Reinstall the same bytes from a different source path; original provenance must survive.
C=fixture('same-content');run(['install','--from',C]);assert tree(entry)==baseline;assert current()==old
record('same-ID at different source preserves original provenance')
run(['install','--from',entry/'source']);assert tree(entry)==baseline;assert current()==old;record('same-ID reinstall from installed source preserves entry')
# Every injected publication boundary has a distinct source identity.
pre=['after-snapshot','copy-chunk','after-copy','git-step','after-index','before-document','after-document','before-entry-rename']
post=['after-entry-rename','after-entry-sync','before-current-write','after-current-write','before-current-rename']
selected=['after-current-rename','after-current-sync']
for point in pre+post+selected:
 p=fixture('fail-'+point);(p/'src/lib.rs').write_text('// '+point+'\n');before=set((STORE/'entries').iterdir());result=run(['install','--from',p],dict(E,RNX_INSTALL_FAIL=point),False)
 if point in selected:
  assert 'selection may already have changed' in result.stderr;assert current()!=old;run(['select',aid])
 elif point in post:
  assert 'installed but not selected' in result.stderr;new=set((STORE/'entries').iterdir())-before;assert len(new)==1;newid=new.pop().name;run(['select',newid]);run(['select',aid])
 else:assert set((STORE/'entries').iterdir())==before
 unchanged(old);record('publication '+point,error=result.stderr.strip())
# Invalid documents and corrupt entries are never repaired in place.
for label,change in [('unknown field',lambda d:d.update(extra=True)),('wrong format',lambda d:d.update(format=99)),('invalid ID',lambda d:d.update(id='../escape')),('bad time',lambda d:d.update(installed_utc='2026-99-99T99:99:99Z')),('bad tool digest',lambda d:d.update(tool_sha256='x'))]:
 p=entry/'installation.json';raw=p.read_bytes();d=json.loads(raw);change(d);p.write_text(json.dumps(d));bad=tree(entry);run(['install','--from',A],ok=False);assert tree(entry)==bad;unchanged(old);p.write_bytes(raw);record('metadata '+label)
p=entry/'source/src/lib.rs';raw=p.read_bytes();p.write_bytes(b'corrupt source');bad=tree(entry);run(['install','--from',A],ok=False);assert tree(entry)==bad;p.write_bytes(raw);unchanged(old);record('corrupt same-ID source refuses, never overwrites')
for label,payload in [('oversized',b' '*65537),('unknown',b'{"format":1,"id":"'+aid.encode()+b'","extra":1}'),('traversal',b'{"format":1,"id":"../escape"}')]:
 (STORE/'current.json').write_bytes(payload);run(['show'],ok=False);assert current()==payload;(STORE/'current.json').write_bytes(old);record('current '+label)
# Missing/dirty/index/file-name/source-closure refusals.
for label in ['missing','untracked','unmerged','symlink','fifo','nonunicode','backslash','bad-layout','absolute-path','dependency-escape','target-escape','build-escape','dev-escape','patch-escape','replace-escape','workspace-escape','inheritance','glob']:
 p=fixture('invalid-'+label)
 if label=='missing':(p/'src/lib.rs').unlink()
 elif label=='untracked':(p/'extra').write_text('x')
 elif label=='unmerged':
  oid=git(p,'rev-parse','HEAD:src/lib.rs').decode().strip();git(p,'update-index','--force-remove','src/lib.rs');sp.run(['git','-C',str(p),'update-index','--index-info'],input=f'100644 {oid} 1\tsrc/lib.rs\n'.encode(),env=E,check=True)
 elif label in ['symlink','fifo']:
  q=p/'src/lib.rs';q.unlink();q.symlink_to('/etc/passwd') if label=='symlink' else os.mkfifo(q)
 elif label=='nonunicode':
  fd=os.open(os.fsencode(p)+b'/bad\xff',os.O_CREAT|os.O_WRONLY,0o600);os.close(fd);git(p,'add','.')
 elif label=='backslash':(p/'bad\\name').write_text('x');git(p,'add','.')
 elif label=='bad-layout':(p/'Cargo.toml').write_text('[package]\nname="other"\n')
 else:
  blocks={'absolute-path':'[lib]\npath="/etc/passwd"','dependency-escape':'[dependencies]\nx={path="../outside"}','target-escape':'[[bin]]\nname="x"\npath="../outside.rs"','build-escape':'[target.\'cfg(unix)\'.build-dependencies]\nx={path="../outside"}','dev-escape':'[dev-dependencies]\nx={path="../outside"}','patch-escape':'[patch.crates-io]\nx={path="../outside"}','replace-escape':'[replace]\n"x:1.0.0"={path="../outside"}','workspace-escape':'[workspace]\nmembers=["../outside"]','inheritance':'[dependencies]\nx={workspace=true}','glob':'[workspace]\nmembers=["adapters/*"]'}
  raw=(p/'Cargo.toml').read_text();raw=raw.replace('[workspace]\n','') if label in ['workspace-escape','glob'] else raw;(p/'Cargo.toml').write_text(raw+blocks[label]+'\n')
 result=run(['install','--from',p],ok=False);unchanged(old);record('source refusal '+label,error=result.stderr.strip())
# Test-only injectable bounds are no larger than the product constants.
for variable,value in [('RNX_INSTALL_SOURCE_FILES','7'),('RNX_INSTALL_SOURCE_BYTES','1'),('RNX_INSTALL_COPY_BYTES','1'),('RNX_INSTALL_RETAINED_FILES','1'),('RNX_INSTALL_RETAINED_BYTES','1')]:
 p=fixture('limit-'+variable);(p/'src/lib.rs').write_text('// limit '+variable);run(['install','--from',p],dict(E,**{variable:value}),False);unchanged(old);record('allowance '+variable)
# Private path checking, including a user symlink to the selected store.
real=W/'other-data';real.mkdir();link=W/'data-link';link.symlink_to(real,target_is_directory=True);linkenv=dict(E,XDG_DATA_HOME=str(link));lid=installation(run(['install','--from',A],linkenv));assert lid==aid;record('user symlink root allowed')
for label,target in [('entries',STORE/'entries'),('lock',STORE/'install.lock'),('current',STORE/'current.json')]:
 backup=target.with_name(target.name+'.backup');target.rename(backup);target.symlink_to(backup)
 run(['install','--from',A],ok=False);target.unlink();backup.rename(target);unchanged(old);record('managed symlink '+label)
for label,target in [('lock',STORE/'install.lock'),('current',STORE/'current.json')]:
 backup=target.with_name(target.name+'.backup');target.rename(backup);os.mkfifo(target);run(['install','--from',A],ok=False,timeout=10);target.unlink();backup.rename(target);unchanged(old);record('managed FIFO '+label)
# Pauses are released by files; the process always has a bounded parent wait.
def wait(marker,p):
 end=time.monotonic()+20
 while not marker.exists():
  assert p.poll() is None,'process exited before pause'
  if time.monotonic()>end:raise AssertionError('pause timeout')
  time.sleep(.01)
def start(source,point,name):
 marker=W/(name+'.pause');log=(O/(name+'.log')).open('w');env=dict(E,RNX_INSTALL_PAUSE=point,RNX_INSTALL_MARKER=str(marker));p=sp.Popen([str(T),'runtime','install','--from',str(source)],env=env,stdout=log,stderr=sp.STDOUT);return p,marker,log
# Mutation after snapshot (copy), and growth after file open (read bound).
for point in ['after-snapshot','copy-chunk']:
 psrc=fixture('mutation-'+point);(psrc/'src/lib.rs').write_text('// mutation '+point);p,marker,log=start(psrc,point,'mutation-'+point);wait(marker,p)
 q=psrc/('.gitignore' if point=='copy-chunk' else 'src/lib.rs');q.write_bytes(q.read_bytes()+b'changed')
 marker.with_suffix('.release').write_text('go');assert p.wait(timeout=30)!=0;log.close();unchanged(old);record('source mutation '+point)
# Interrupted writer leaves selection intact. Post-rename interruption retains a selectable entry.
for point in ['copy-chunk','git-step','after-entry-rename']:
 for sig in [signal.SIGINT,signal.SIGTERM]:
  name=f'interrupt-{point}-{sig}';src=fixture(name);(src/'src/lib.rs').write_text('// '+name);before=set((STORE/'entries').iterdir());p,marker,log=start(src,point,name);wait(marker,p);p.send_signal(sig);assert p.wait(timeout=10)==128+sig;log.close();unchanged(old)
  new=set((STORE/'entries').iterdir())-before
  if point=='after-entry-rename':assert len(new)==1;run(['select',new.pop().name]);run(['select',aid]);assert 'installed but not selected' in (O/(name+'.log')).read_text()
  else:assert not new
  record(name,signal_status=128+sig)
# Two writers of the same snapshot: one publishes, the waiter reuses the complete entry.
src=fixture('concurrent');(src/'src/lib.rs').write_text('// concurrent');p,marker,log=start(src,'after-copy','writer');wait(marker,p)
q,qmarker,qlog=start(src,'waiting','waiter');wait(qmarker,q);qmarker.with_suffix('.release').write_text('go');marker.with_suffix('.release').write_text('go');assert p.wait(timeout=30)==0;assert q.wait(timeout=30)==0;log.close();qlog.close();assert (O/'writer.log').read_text().splitlines()[0]==(O/'waiter.log').read_text().splitlines()[0];run(['select',aid]);record('concurrent same-ID installer reuses publication')
# A killed waiter owns no stage; the writer still completes.
src=fixture('killed-waiter');(src/'src/lib.rs').write_text('// killed waiter');p,marker,log=start(src,'after-copy','writer2');wait(marker,p);q,qmarker,qlog=start(src,'waiting','waiter2');wait(qmarker,q);q.kill();assert q.wait(timeout=10)==-signal.SIGKILL;qlog.close();marker.with_suffix('.release').write_text('go');assert p.wait(timeout=30)==0;log.close();run(['select',aid]);unchanged(old);record('killed lock waiter cannot damage writer')
# A killed copying writer leaves only an undiscoverable stage; retry under lock reclaims it.
src=fixture('killed-writer');(src/'src/lib.rs').write_text('// killed writer');p,marker,log=start(src,'after-copy','writer3');wait(marker,p);p.kill();assert p.wait(timeout=10)==-signal.SIGKILL;log.close();assert current()==old;assert list(STORE.glob('.stage-*'));run(['install','--from',src]);assert not list(STORE.glob('.stage-*'));run(['select',aid]);record('killed copying writer stage reclaimed by retry')

# Actual Git exec, not just a pre-exec hook pause: no inherited install lock.
traps=W/'traps';traps.mkdir();real=shutil.which('git');gitlog=W/'git-exec.jsonl'
script=traps/'git';script.write_text("""#!/usr/bin/python3
import os,sys,json,time,subprocess
from pathlib import Path
args=sys.argv[1:];fds=[]
for p in Path('/proc/self/fd').iterdir():
 try:fds.append(os.readlink(p))
 except FileNotFoundError:pass
assert not any(p.endswith('/install.lock') for p in fds),fds
with open(os.environ['INSTALL_GIT_LOG'],'a') as f:f.write(json.dumps({'pid':os.getpid(),'args':args,'lock_inherited':False})+'\\n')
if 'hash-object' in args and '-w' in args:
 mode=os.environ.get('INSTALL_GIT_MODE','')
 if mode=='fail':print('injected Git failure',file=sys.stderr);raise SystemExit(7)
 if mode=='stdout':sys.stdout.buffer.write(b'x'*(16*1024*1024+1));sys.stdout.flush();time.sleep(60)
 if mode=='stderr':sys.stderr.buffer.write(b'x'*(16*1024*1024+1));sys.stderr.flush();time.sleep(60)
 if mode=='hang':
  child=subprocess.Popen(['/bin/sleep','60'])
  Path(os.environ['INSTALL_GIT_PID']).write_text(json.dumps([os.getpid(),child.pid]))
  time.sleep(60)
os.execv(REAL,[REAL,*args])
""".replace('REAL',repr(real)).replace("+'\\\\n'", "+'\\n'"));script.chmod(0o755)
trapenv=dict(E,PATH=str(traps)+':'+E['PATH'],INSTALL_GIT_LOG=str(gitlog))
for mode in ['fail','stdout','stderr']:
 src=fixture('git-'+mode);(src/'src/lib.rs').write_text('// Git '+mode)
 result=run(['install','--from',src],dict(trapenv,INSTALL_GIT_MODE=mode),False);unchanged(old);record('Git '+mode+' failure is bounded and reaped',error=result.stderr[:300])
for sig in [signal.SIGINT,signal.SIGTERM]:
 src=fixture('git-hang-'+str(sig));(src/'src/lib.rs').write_text('// Git hang '+str(sig));marker=W/('git-pids-'+str(sig));log=(O/('git-hang-'+str(sig)+'.log')).open('w')
 p=sp.Popen([str(T),'runtime','install','--from',str(src)],env=dict(trapenv,INSTALL_GIT_MODE='hang',INSTALL_GIT_PID=str(marker)),stdout=log,stderr=sp.STDOUT);wait(marker,p);children=json.loads(marker.read_text());p.send_signal(sig);assert p.wait(timeout=10)==128+sig;log.close();unchanged(old)
 # A descendant orphan can briefly remain a zombie awaiting init; it cannot run or hold FDs.
 for child in children:
  stat=Path('/proc',str(child),'stat');assert not stat.exists() or stat.read_text().split(') ',1)[1].startswith('Z ')
 record('interrupt active Git '+str(sig),children=children,no_live_child=True)
assert gitlog.exists();records=[json.loads(line) for line in gitlog.read_text().splitlines()];assert records and all(not r['lock_inherited'] for r in records);(O/'git-exec.jsonl').write_bytes(gitlog.read_bytes());record('writer lock close-on-exec on every observed Git child',execs=len(records))
# Filter and routing control retained from gate one against the product installer.
src=fixture('hostile');(src/'payload.txt').write_bytes(b'raw\r\nCRLF\r\n');(src/'.gitattributes').write_text('*.txt filter=hostile text\n');git(src,'add','.');git(src,'-c','user.name=Fixture','-c','user.email=fixture@invalid','-c','commit.gpgsign=false','commit','-qm','attributes')
marker=W/'filter-marker';filterfile=W/'filter.py';filterfile.write_text('from pathlib import Path\nimport sys\nPath('+repr(str(marker))+').write_text("ran")\nsys.stdout.write("FILTERED")\n'.replace('\\n','\n'))
git(src,'config','filter.hostile.clean','python3 '+str(filterfile));git(src,'config','filter.hostile.required','true');git(src,'config','core.autocrlf','true');git(src,'add','payload.txt');assert marker.exists() and git(src,'show',':payload.txt')==b'FILTERED';marker.unlink()
env=dict(E,GIT_DIR=str(A/'.git'),GIT_WORK_TREE=str(A),GIT_INDEX_FILE=str(A/'.git/index'),GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.autocrlf',GIT_CONFIG_VALUE_0='true')
hid=installation(run(['install','--from',src],env));assert not marker.exists();assert (STORE/'entries'/hid/'source/payload.txt').read_bytes()==b'raw\r\nCRLF\r\n';run(['select',aid]);record('hostile filter positive control, raw provenance and Git routing')
# Exact source bounds and retained-tree boundaries, followed by one-under refusals.
files=git(A,'ls-files','-z').split(b'\0')[:-1];size=sum((A/os.fsdecode(p)).stat().st_size for p in files)
run(['install','--from',A],dict(E,RNX_INSTALL_SOURCE_FILES=str(len(files)),RNX_INSTALL_SOURCE_BYTES=str(size)))
for key,value in [('RNX_INSTALL_SOURCE_FILES',len(files)-1),('RNX_INSTALL_SOURCE_BYTES',size-1)]:run(['install','--from',A],dict(E,**{key:str(value)}),False);unchanged(old)
record('exact source allowances and one-under refusals',files=len(files),bytes=size)
allpaths=list(entry.rglob('*'));retained=sum(p.stat().st_size for p in allpaths if p.is_file());n=len(allpaths)
run(['select',aid],dict(E,RNX_INSTALL_RETAINED_FILES=str(n),RNX_INSTALL_RETAINED_BYTES=str(retained)))
for key,value in [('RNX_INSTALL_RETAINED_FILES',n-1),('RNX_INSTALL_RETAINED_BYTES',retained-1)]:run(['select',aid],dict(E,**{key:str(value)}),False);unchanged(old)
record('exact retained allowances and one-under refusals',entries=n,bytes=retained)
src=fixture('copy-read-bound');(src/'src/lib.rs').write_text('// copy read bound');readlog=W/'read.jsonl';run(['install','--from',src],dict(E,RNX_INSTALL_COPY_BYTES='1',RNX_INSTALL_READ_LOG=str(readlog)),False);reads=[json.loads(l) for l in readlog.read_text().splitlines()];assert sum(r['bytes'] for r in reads)==2;unchanged(old);record('copy read limited to allowance plus one detection byte',read_bytes=2,allowance=1)
# A selector queues behind a writer and revalidates only after acquiring the lock.
src=fixture('selector-wait');(src/'src/lib.rs').write_text('// selector wait');p,marker,log=start(src,'after-copy','writer4');wait(marker,p);qmarker=W/'selector.pause';qlog=(O/'selector.log').open('w');q=sp.Popen([str(T),'runtime','select',bid],env=dict(E,RNX_INSTALL_PAUSE='waiting',RNX_INSTALL_MARKER=str(qmarker)),stdout=qlog,stderr=sp.STDOUT);wait(qmarker,q);qmarker.with_suffix('.release').write_text('go');marker.with_suffix('.release').write_text('go');assert p.wait(timeout=30)==0 and q.wait(timeout=30)==0;log.close();qlog.close();assert json.loads(current())['id']==bid;run(['select',aid]);record('selector waits, revalidates, selects after publication')
for label,env in [('empty-data',dict(E,XDG_DATA_HOME='')),('relative-data',dict(E,XDG_DATA_HOME='relative')),('source-containment',dict(E,XDG_DATA_HOME=str(A/'data'))),('cache-containment',dict(E,RNX_PROJECT_CACHE=str(STORE/'cache'))),('scratch-containment',dict(E,XDG_STATE_HOME=str(STORE/'state')))]:
 run(['install','--from',A],env,False);unchanged(old);record('store refusal '+label)
# No commit is needed to install a staged snapshot; provenance must say so.
src=fixture('uncommitted');git(src,'update-ref','-d','HEAD');(src/'src/lib.rs').write_text('// unborn snapshot');uid=installation(run(['install','--from',src]));d=json.loads((STORE/'entries'/uid/'installation.json').read_text());assert d['source_commit'] is None and d['dirty_tracked'];run(['select',aid]);record('uncommitted index installs without synthetic commit')
# A real linked worktree remains a supported source, with fresh independent administration.
linked=W/'linked';git(A,'worktree','add','--detach',str(linked),'HEAD');(linked/'src/lib.rs').write_text('// linked snapshot');lid=installation(run(['install','--from',linked]));assert (linked/'.git').is_file();assert (STORE/'entries'/lid/'source/.git').is_dir();assert not (STORE/'entries'/lid/'source/.git/commondir').exists();run(['select',aid]);record('linked worktree installs independent Git administration')
# Metadata and object corruption is a refusal, not an attempted repair.
p=entry/'installation.json';raw=p.read_bytes();p.write_bytes(b' '*65537);run(['select',aid],ok=False);assert p.stat().st_size==65537;p.write_bytes(raw);unchanged(old);record('oversized installation metadata refused unchanged')
object_file=next(p for p in (entry/'source/.git/objects').glob('*/*') if p.is_file());raw=object_file.read_bytes();mode=object_file.stat().st_mode;object_file.chmod(0o600);object_file.write_bytes(b'broken');run(['install','--from',A],ok=False);assert object_file.read_bytes()==b'broken';object_file.write_bytes(raw);object_file.chmod(mode);unchanged(old);record('corrupt independent Git object refused unchanged')
# Relative --from resolves at the caller, and a nested package is not a runtime root.
run(['install','--from',os.path.relpath(A,Path.cwd())]);assert current()==old;run(['install','--from',A/'adapters/polars'],ok=False);unchanged(old);record('relative source accepted, nested Git root refused')
# Filesystem-monitor hooks are not allowed to refresh the source index either.
src=fixture('fsmonitor');(src/'src/lib.rs').write_text('// fsmonitor snapshot');mark=W/'fsmonitor-ran';hook=W/'fsmonitor.py';hook.write_text('#!/usr/bin/python3\nfrom pathlib import Path\nimport sys\nPath('+repr(str(mark))+').write_text("ran")\nsys.stdout.buffer.write(b"token\\0")\n');hook.chmod(0o755);git(src,'config','core.fsmonitor',str(hook));git(src,'ls-files','--stage');assert mark.exists();mark.unlink();before_source=tree(src);run(['install','--from',src]);assert not mark.exists() and tree(src)==before_source;run(['select',aid]);record('filesystem monitor positive control, no hook or optional source-index writes')
(O/'tool.json').write_text(json.dumps({'path':str(T),'sha256':hashlib.sha256(T.read_bytes()).hexdigest(),'groups':len(rows)},indent=2)+'\n');print('PASS installer matrix',len(rows),flush=True)
