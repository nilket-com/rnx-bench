from pathlib import Path
import json,os,subprocess as sp,tempfile,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];O=Path(os.environ.get('RNX_REMOVAL_RESULTS',str(B/'results/removal-ownership-0066'))).resolve();O.mkdir(parents=True,exist_ok=True);assert not (O/'bootstrap.json').exists()
with tempfile.TemporaryDirectory(prefix='rnx-0066-bwrap-') as t:
 p=Path(t);entry=p/'store/entries'/('a'*64);outside=p/'outside';outside.mkdir();(outside/'sentinel').write_text('fixture only')
 for n in ['mnt','out']:(entry/n).mkdir(parents=True)
 code='''import os,json,sys
from pathlib import Path
p=Path(sys.argv[1]);e=Path(sys.argv[2]);uid=int(sys.argv[3]);assert os.getuid()==uid
assert e.stat().st_dev==(e/'mnt').stat().st_dev==(p/'outside').stat().st_dev
assert (e/'out').stat().st_dev!=e.stat().st_dev
assert (e/'mnt/sentinel').read_text()=='fixture only'
rows=[x for x in Path('/proc/self/mountinfo').read_text().splitlines() if str(e) in x]
assert len(rows)==2,rows
os.unlink(e/'mnt/sentinel')
assert not (p/'outside/sentinel').exists()
print(json.dumps(dict(uid=uid,entry_dev=e.stat().st_dev,bind_dev=(e/'mnt').stat().st_dev,tmpfs_dev=(e/'out').stat().st_dev,mountinfo=rows,unguarded_unlink_reaches_outside_fixture=True)))
'''
 args=[shutil.which('bwrap'),'--unshare-user','--uid',str(os.getuid()),'--gid',str(os.getgid()),'--bind','/','/','--dev','/dev','--proc','/proc','--bind',str(outside),str(entry/'mnt'),'--tmpfs',str(entry/'out'),'--','python3','-c',code,str(p),str(entry),str(os.getuid())]
 r=sp.run(args,capture_output=True,text=True,timeout=20);assert r.returncode==0,(r.stdout,r.stderr);result=json.loads(r.stdout);result.update(command=args,stderr=r.stderr)
 assert not (outside/'sentinel').exists();assert not (entry/'mnt/sentinel').exists();result['parent_has_no_mounts']=not any(str(entry) in x for x in Path('/proc/self/mountinfo').read_text().splitlines())
(O/'bootstrap.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS unprivileged bubblewrap nested/bind fixtures and outside-fixture positive control')
