"""Final tool and same-snapshot runtime; cold installed :dep journeys."""
from pathlib import Path
import subprocess as sp,json,os,shutil,tarfile,io,hashlib,sys
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target/installed';O=B/'results/inventory-final-0065/installed';assert not W.exists();W.mkdir();O.mkdir();C=W/'original';C.mkdir()
raw=sp.check_output(['git','-C',R,'archive','4855dbd']);
with tarfile.open(fileobj=io.BytesIO(raw)) as tar:tar.extractall(C,filter='data')
E={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','RNX_','CARGO_','RUST'))};E['PYTHONDONTWRITEBYTECODE']='1'
for args in [['init','-q'],['add','.'],['-c','user.name=Fixture','-c','user.email=f@invalid','-c','commit.gpgsign=false','commit','-qm','0065 final source snapshot']]:sp.run(['git','-C',C,*args],env=E,check=True)
commit=sp.check_output(['git','-C',C,'rev-parse','HEAD'],env=E,text=True).strip();(O/'snapshot-build.json').write_text(json.dumps(dict(baseline='4855dbd',fixture_commit=commit,source_archive_sha256=hashlib.sha256(raw).hexdigest(),build='ordinary tool and launcher built from identical committed source in root regression, then copied here; no prototype patch'),indent=2)+'\n')
(W/'bin').mkdir();shutil.copy2(H/'target/tool',W/'bin/rnx-project');shutil.copy2(R/'target/release/rnx',W/'bin/rnx')
# Small fixture-only BLAKE3 helper links the exact product dependency for checking
# document tool digests and the later historical-protocol key adaptation.
b3=H/'target/b3';assert b3.exists()
p=B/'probes/runtime-installed-journey/journey.py';s=p.read_text().replace("H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target'",f"H=Path({str(H)!r});B=Path({str(B)!r});W=Path({str(W)!r})").replace("O=B/'results/runtime-installed-journey-0064'",f"O=Path({str(O)!r})")
s=s.replace("doc['tool_sha256']==hashlib.sha256(T.read_bytes()).hexdigest()", "doc['tool_blake3']==sp.check_output(["+repr(str(b3))+"],input=T.read_bytes()).decode().strip()")
s=s.replace("tree_sha256=doc['tree_sha256']","tree_blake3=doc['tree_blake3']")
dest=O/'journey-driver.py';dest.write_text(s)
with (O/'run.log').open('w') as f:sp.run([sys.executable,dest],env=E,stdout=f,stderr=sp.STDOUT,check=True)
print('PASS final installed discovery, cold Polars and combined builds, trapped second consumers, typed SQL and error recovery',flush=True)
