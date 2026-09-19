"""An authentic installation clone fails authentication but remains removable."""
from pathlib import Path
import os,json,shutil,subprocess as sp,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target/real';O=B/'results/removal-storage-0066';E=json.loads((W/'env.json').read_text());d=json.loads((W/'setup.json').read_text());T=Path(d['tool']);original=Path(d['store']);selection=(original/'current.json').read_bytes();key=json.loads(selection)['id'];source=original/'entries'/key
root=W/'corruption-data/rnx/runtimes';assert not root.exists();os.umask(0o077);root.joinpath('entries').mkdir(parents=True);(root/'install.lock').touch();target=root/'entries'/key;shutil.copytree(source,target)
# Keep the authentic document and key, damage only one object body.
doc=(target/'installation.json').read_bytes();blob=next(q for q in (target/'source/.git/objects').glob('*/*') if q.is_file());blob.chmod(0o600);blob.write_bytes(blob.read_bytes()+b'corrupt')
env=dict(E,XDG_DATA_HOME=str(W/'corruption-data'))
p=sp.run([str(T),'runtime','select',key],env=env,capture_output=True,text=True);assert p.returncode!=0 and 'corrupt installed runtime' in p.stderr,(p.stdout,p.stderr)
assert (target/'installation.json').read_bytes()==doc and not (root/'current.json').exists()
r=sp.run([str(T),'runtime','remove',key,'--root',str(root),'--quiescent'],env=env,capture_output=True,text=True);assert r.returncode==0,(r.stdout,r.stderr)
assert not target.exists() and not (root/'current.json').exists() and (original/'current.json').read_bytes()==selection
(O/'corrupt.json').write_text(json.dumps(dict(authentic_id=key,authentication_refused=p.stderr,removal_succeeded=True,document_untouched_before_removal=True,real_selection_unchanged=True,report=r.stdout),indent=2)+'\n')
print('PASS authentic corrupt clone refuses select and permits explicit removal')
