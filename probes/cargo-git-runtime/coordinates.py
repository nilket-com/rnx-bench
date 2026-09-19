from common import *
import shutil
repo=T/'coordinate-repo-v2'
assert not repo.exists(), 'use a fresh target for coordinates'
run(['git','clone','--quiet','--no-hardlinks',B.parent/'rnx',repo])
git(repo,'checkout','--quiet','--detach',REV)
shutil.copytree(P/'coordinate-fixture',repo/'coordinate-fixture')
git(repo,'add','coordinate-fixture')
git(repo,'-c','user.name=Probe','-c','user.email=probe@example.invalid','-c','commit.gpgsign=false','commit','-m','fixture: observe Cargo build coordinates')
rev=git(repo,'rev-parse','HEAD').stdout.decode().strip()
# Archive a bundle so this fixture revision remains reproducible after squash or cleanup.
git(repo,'bundle','create',O/'coordinate-fixture.bundle','HEAD','^'+REV)
rows={}
def install(name,args,expected_dirty):
 dest=T/('installed-v2-'+name)
 run(['cargo','install',*args,*([] if '--git' in args else ['--offline']),'--root',dest,'--target-dir',T/('coordinate-target-v2-'+name),'--force'],timeout=120)
 exe=dest/'bin/rnx-coordinate-probe';p=run([exe]);out=dict(l.split('=',1) for l in p.stdout.decode().splitlines());assert out['dirty']==str(expected_dirty).lower(),out
 r=run([exe,'--require-clean'],ok=False);assert (r.returncode!=0)==expected_dirty
 rows[name]=out|{'refusal':r.stderr.decode(),'exit':r.returncode}
install('path',['--path',repo/'coordinate-fixture'],False)
assert rows['path']['revision']==rev
install('git',['--git',repo.as_uri(),'--rev',rev,'rnx-coordinate-probe'],False)
assert rows['git']['revision']==rev
f=repo/'README.md';old=f.read_bytes();f.write_bytes(old+b'\nDirty fixture.\n')
install('dirty',['--path',repo/'coordinate-fixture'],True)
f.write_bytes(old)
# Hostile filter cannot hide the raw dirty byte.
(repo/'.git/info/attributes').write_text('README.md filter=hide\n')
git(repo,'config','filter.hide.clean','cat /dev/null')
f.write_bytes(old+b'\nDirty fixture.\n')
install('filter-dirty',['--path',repo/'coordinate-fixture'],True)
f.write_bytes(old);(repo/'.git/info/attributes').unlink()
# No .git: unknown, never a fabricated clean coordinate.
no=T/'coordinate-no-git-v2';shutil.copytree(repo/'coordinate-fixture',no,ignore=shutil.ignore_patterns('target'))
install('no-git',['--path',no],True)
assert rows['no-git']['revision']=='unknown'
save('coordinates.json',{'fixture_revision':rev,'base':REV,'rows':rows,'qualification':'instrumented fixture in exact repository topology, not production provenance code; no new rnx protocol implemented'})
print('Coordinates pass',flush=True)
