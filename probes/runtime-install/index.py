"""Independent-index and working-byte controls, including linked worktrees and hostile Git."""
from pathlib import Path
import subprocess as sp, os, json, hashlib, shutil
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/runtime-install-0064';T=W/'bin/rnx-project';F=W/'index-controls';F.mkdir()
e={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};e.update(GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1')
def git(p,*a):return sp.check_output(['git','-C',str(p),*a],env=e,stderr=sp.PIPE)
def probe(*a,env=e):
 p=sp.run([str(T),'runtime-probe',*map(str,a)],env=env,capture_output=True,text=True,timeout=30)
 assert p.returncode==0,(a,p.stdout,p.stderr)
 return json.loads(p.stdout)
def init(p):p.mkdir();git(p,'init','-q','--template=')
def commit(p):
 git(p,'add','.');git(p,'-c','user.name=Fixture','-c','user.email=fixture@invalid','-c','commit.gpgsign=false','commit','-qm','fixture')
def independent(p):
 g=p/'.git';assert g.is_dir() and not g.is_symlink()
 assert not (g/'objects/info/alternates').exists() and not (g/'commondir').exists() and not (g/'gitdir').exists()
 config=(g/'config').read_text();assert 'worktree' not in config.lower() and 'remote ' not in config and 'filter ' not in config
 assert not any((g/'hooks').glob('*'))
 # Every staged blob actually exists in this independent object database.
 records=git(p,'ls-files','--stage','-z').split(b'\0');count=0
 for r in filter(None,records):
  meta,path=r.split(b'\t',1);mode,oid,stage=meta.split();assert stage==b'0'
  raw=git(p,'cat-file','blob',oid.decode());assert raw==(p/os.fsdecode(path)).read_bytes();count+=1
 return count
rows={}
p=F/'ordinary';init(p)
for name,raw in [('plain.txt',b'one\r\ntwo\r\n'),('space quote \' " 🦀.txt',b'utf8\x00bytes'),('line\nbreak,comma.txt',b'newline path'),('executable.sh',b'#!/bin/sh\nexit 0\n'),('.gitignore',b'ignored/\n')]: (p/name).write_bytes(raw)
(p/'executable.sh').chmod(0o755);commit(p)
(p/'plain.txt').write_bytes(b'DIRTY\r\nworking bytes\r\n');(p/'ignored').mkdir();(p/'ignored/secret').write_text('must not copy')
source=probe('fingerprint',p);d=probe('install',p,F/'ordinary-store');dest=F/'ordinary-store/entries'/d['id']/'source'
assert d['dirty_tracked'];assert probe('fingerprint',dest)['sha256']==source['sha256'];assert independent(dest)==len(source['files']);assert not (dest/'ignored').exists()
rows['dirty_modes_odd_names']={'source_sha256':source['sha256'],'installed_sha256':d['tree_sha256'],'files':d['files'],'ignored_excluded':True,'independent_blobs':True}
# Real linked worktree with a .git routing file. Installation must not copy it.
linked=F/'linked';git(p,'worktree','add','--detach',str(linked),'HEAD');assert (linked/'.git').is_file();(linked/'plain.txt').write_bytes(b'linked dirty bytes\n')
ld=probe('install',linked,F/'linked-store');ldest=F/'linked-store/entries'/ld['id']/'source';assert independent(ldest)==ld['files'];assert (ldest/'plain.txt').read_bytes()==b'linked dirty bytes\n'
# Remove both source routes before proving object and inventory independence again.
linked.rename(F/'linked-unavailable');p.rename(F/'ordinary-unavailable');assert not linked.exists() and not p.exists();assert independent(ldest)==ld['files'];assert probe('fingerprint',ldest)['sha256']==ld['tree_sha256']
rows['linked_worktree']={'source_git_was_file':True,'source_and_common_repo_renamed':True,'installed_sha256':ld['tree_sha256'],'objects_and_fingerprint_still_work':True}
# Source attributes/config/global routing must never run a filter while copying or indexing.
h=F/'hostile';init(h);(h/'payload.txt').write_bytes(b'CRLF\r\nUNCHANGED\r\n');(h/'.gitattributes').write_text('*.txt filter=hostile text\n');commit(h)
marker=F/'filter-ran';filter_script=F/'filter.py';filter_script.write_text('from pathlib import Path\nimport sys\nPath('+repr(str(marker))+').write_text("ran")\nsys.stdout.write("CORRUPTED")\n')
filter_command='python3 '+str(filter_script)
git(h,'config','filter.hostile.clean',filter_command);git(h,'config','filter.hostile.required','true');git(h,'config','core.autocrlf','true')
# Positive control: ordinary git add invokes the hostile filter and changes its blob.
git(h,'add','payload.txt');assert marker.exists();assert git(h,'show',':payload.txt')==b'CORRUPTED';marker.unlink()
trap=F/'routing';init(trap);(trap/'wrong').write_text('wrong repo');commit(trap)
config=F/'global-config';config.write_text('[core]\n autocrlf=true\n[filter "hostile"]\n clean='+filter_command+'\n required=true\n')
hostile=dict(e,GIT_DIR=str(trap/'.git'),GIT_WORK_TREE=str(trap),GIT_INDEX_FILE=str(trap/'.git/index'),GIT_OBJECT_DIRECTORY=str(trap/'.git/objects'),GIT_ALTERNATE_OBJECT_DIRECTORIES=str(trap/'.git/objects'),GIT_CONFIG_GLOBAL=str(config),GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.autocrlf',GIT_CONFIG_VALUE_0='true')
hd=probe('install',h,F/'hostile-store',env=hostile);hdest=F/'hostile-store/entries'/hd['id']/'source';assert not marker.exists();assert (hdest/'payload.txt').read_bytes()==b'CRLF\r\nUNCHANGED\r\n';assert not (hdest/'wrong').exists();assert independent(hdest)==hd['files'];assert probe('fingerprint',h,env=hostile)['sha256']==hd['tree_sha256']
rows['hostile_git']={'positive_filter_control':True,'no_filter_during_install':True,'crlf_preserved':True,'routing_ignored':True,'installed_sha256':hd['tree_sha256']}
# Existing fingerprint refusals remain: unsupported paths, index states and file kinds.
for label,kind in [('symlink','symlink'),('fifo','fifo'),('untracked','untracked'),('backslash','backslash'),('nonunicode','nonunicode')]:
 q=F/label;init(q);(q/'tracked').write_text('a');commit(q)
 if kind=='symlink':(q/'tracked').unlink();(q/'tracked').symlink_to('missing')
 elif kind=='fifo':(q/'tracked').unlink();os.mkfifo(q/'tracked')
 elif kind=='untracked':(q/'extra').write_text('x')
 elif kind=='backslash':(q/'bad\\name').write_text('x');git(q,'add','.')
 else:
  raw=os.fsencode(q)+b'/bad\xff';fd=os.open(raw,os.O_CREAT|os.O_WRONLY,0o600);os.close(fd);git(q,'add','.')
 result=sp.run([str(T),'runtime-probe','install',str(q),str(F/(label+'-store'))],env=e,capture_output=True,text=True,timeout=10)
 assert result.returncode!=0 and not (F/(label+'-store')).exists(),(label,result.stdout,result.stderr)
 rows[label]={'refused':True,'error':result.stderr.strip()}
(O/'index.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS independent index and refusal controls',flush=True)
