from common import *
import shutil, tarfile, io, tempfile
s=json.loads((O/'setup.json').read_text());source=Path(s['source']);target=T/'build-target';rows={}
trap=T/'traps';trap.mkdir(exist_ok=True);trace=T/'fetch-attempt'
(trap/'cargo').write_text('#!/bin/sh\nprintf "attempt\\n" >> '+str(trace)+'\nexit 77\n');(trap/'cargo').chmod(0o755)
assert run([trap/'cargo'],ok=False).returncode==77;trace.unlink()
ns=['bwrap','--unshare-user','--uid',str(os.getuid()),'--gid',str(os.getgid()),'--unshare-net','--bind','/','/','--dev','/dev','--proc','/proc','--']
def inspect(name,exe,state,rev=None):
 row=json.loads(run([exe,'--probe-coordinates']).stdout);assert row['state']==state,(name,row)
 if rev:assert row['rev']==rev,(name,row)
 env=ENV|{'PATH':str(trap)+':'+ENV['PATH'],'RNX_PROBE_REQUEST_DIR':str(T/('decline-'+name))}
 for args in [[],['--decline']]+([['--consent']] if state in ['dirty','unknown'] else []):
  p=run(ns+['strace','-f','-e','trace=network','-o',O/(name+'-refusal.trace'),exe,'--probe-dep',*args],env=env,ok=False)
  assert p.returncode==(2 if state in ['dirty','unknown'] else 0),(name,p.stderr)
  assert not trace.exists() and not (T/('decline-'+name)).exists()
  assert 'AF_INET' not in (O/(name+'-refusal.trace')).read_text()
  if state in ['dirty','unknown']:assert b'RNX_DEP_RUNTIME=' in p.stderr
 row['decline_or_refusal']=p.stderr.decode();rows[name]=row;save('coordinates.json',rows)
 print(name,state,flush=True)
 return exe

def install_path(name,root=source,state='unverified',rev=None,extra=None):
 env=ENV|(extra or {})
 p=run(ns+['cargo','install','--path',root,'--offline','--locked','--root',T/'install-path','--target-dir',target,'--force'],env=env,timeout=1200)
 (O/(name+'-build.stderr')).write_bytes(p.stderr)
 return inspect(name,T/'install-path/bin/rnx',state,rev)
if os.environ.get('RNX_PROBE_RESUME'):
 rows=json.loads((O/'coordinates.json').read_text());unpushed=rows['path-unpublished']['rev']
 p=run([T/'install-path/bin/rnx','--probe-dep','--consent'],env=ENV|{'RNX_PROBE_REQUEST_DIR':str(T/'request-unpublished')},ok=False,timeout=180)
 assert p.returncode==3 and unpushed.encode() in p.stderr and b'not found' in p.stderr and b'RNX_DEP_RUNTIME=' in p.stderr
 rows['path-unpublished']['consented_failure']=p.stderr.decode();save('coordinates.json',rows)
else:
 inspect('git-fresh',T/'install-git1/bin/rnx','acquired',s['rev1'])
 for name,rev in [('git-rev2',s['rev2']),('git-cached-rev1',s['rev1'])]:
  p=run(['cargo','install','--git',s['url'],'--rev',rev,'rnx','--locked','--root',T/name,'--target-dir',target,'--force'],timeout=1200)
  (O/(name+'-build.stderr')).write_bytes(p.stderr);inspect(name,T/name/'bin/rnx','acquired',rev)
 exe=install_path('path-pushed',rev=s['rev1'])
 p=run([exe,'--probe-dep','--consent'],env=ENV|{'RNX_PROBE_REQUEST_DIR':str(T/'request-pushed')},timeout=180);assert p.returncode==0
 rows['path-pushed']['consented_acquisition']='passed without runtime override';save('coordinates.json',rows)
 f=source/'README.md';original=f.read_bytes();stamp=f.stat()
 f.write_bytes(original+b'\nDirty behind filter.\n')
 (source/'.git/info/attributes').write_text('README.md filter=hide\n');git(source,'config','filter.hide.clean','git show HEAD:README.md')
 assert git(source,'diff','--exit-code','--','README.md',ok=False).returncode==0
 install_path('dirty-filter',state='dirty',rev=s['rev1'])
 f.write_bytes(original);(source/'.git/info/attributes').unlink();git(source,'config','--remove-section','filter.hide')
 added=source/'coordinate-staged.txt';added.write_text('added\n');git(source,'add',added)
 install_path('staged-add',state='dirty',rev=s['rev1']);git(source,'reset','HEAD','--','coordinate-staged.txt');added.unlink()
 deleted='plans/0066_removal_is_an_explicit_ownership_decision.md';git(source,'rm',deleted)
 install_path('staged-delete',state='dirty',rev=s['rev1']);git(source,'restore','--staged','--worktree',deleted)
 mode=f.stat().st_mode;before=f.stat().st_mtime_ns;f.chmod(mode^0o111);assert f.stat().st_mtime_ns==before
 install_path('mode-only',state='dirty',rev=s['rev1']);f.chmod(mode)
 install_path('restored-clean',rev=s['rev1'])
 # Clean, unpublished revision: do not fetch to classify; consent attempts acquisition.
 f.write_bytes(original+b'\nUnpublished coordinate fixture.\n');git(source,'add','README.md');git(source,'-c','user.name=Probe','-c','user.email=probe@example.invalid','commit','--quiet','-m','fixture: unpublished coordinate')
 unpushed=git(source,'rev-parse','HEAD').stdout.decode().strip();git(source,'bundle','create',O/'unpublished.bundle','HEAD','^94f5f3f')
 exe=install_path('path-unpublished',rev=unpushed)
 p=run([exe,'--probe-dep','--consent'],env=ENV|{'RNX_PROBE_REQUEST_DIR':str(T/'request-unpublished')},ok=False,timeout=180)
 assert p.returncode==3 and unpushed.encode() in p.stderr and b'not found' in p.stderr and b'RNX_DEP_RUNTIME=' in p.stderr
 rows['path-unpublished']['consented_failure']=p.stderr.decode();save('coordinates.json',rows)
git(source,'checkout','--quiet','--detach',s['rev1'])
archive=git(source,'archive',s['rev1']).stdout
outer=T/'unrelated-outer';outer.mkdir(exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:tar.extractall(outer,filter='data')
install_path('unrelated-outer',root=outer,state='unknown',rev='unknown')
with tempfile.TemporaryDirectory(prefix='rnx-0067-no-git-') as tmp:
 with tarfile.open(fileobj=io.BytesIO(archive)) as tar:tar.extractall(tmp,filter='data')
 install_path('no-git-administration',root=tmp,state='unknown',rev='unknown')
missing=T/'missing-git';missing.mkdir(exist_ok=True);(missing/'git').write_text('#!/bin/sh\nexit 127\n');(missing/'git').chmod(0o755)
install_path('missing-git',state='unknown',rev='unknown',extra={'PATH':str(missing)+':'+ENV['PATH']})
print('Real coordinate install matrix passes',flush=True)
