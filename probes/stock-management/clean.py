"""Build the actual port from a clean known-revision fixture checkout."""
from pathlib import Path
import subprocess as sp,json
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/stock-management-0067';S=W/'clean-source'
assert not S.exists()
patch=sp.check_output(['git','diff','--no-color','--binary','HEAD'],cwd=R);(O/'product.patch').write_bytes(patch)
sp.run(['git','clone','--quiet','--no-hardlinks',str(R),str(S)],check=True)
if patch:sp.run(['git','apply','--index','--whitespace=nowarn','-'],input=patch,cwd=S,check=True)
sp.run(['git','-c','commit.gpgsign=false','-c','user.name=Probe','-c','user.email=probe@example.invalid','commit','--allow-empty','--quiet','-m','fixture: 0067 management product port'],cwd=S,check=True)
rev=sp.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()
sp.run(['git','bundle','create',str(O/'clean.bundle'),'HEAD','^4e887b6'],cwd=S,check=True)
with (O/'clean-build.log').open('w') as f:sp.run(['cargo','build','--locked','--offline','--features','test-support','--bin','rnx'],cwd=S,stdout=f,stderr=sp.STDOUT,check=True)
(O/'clean.json').write_text(json.dumps(dict(revision=rev,source=str(S),binary=str(S/'target/debug/rnx'),state='unverified',remote_fetch_attempted=False),indent=2)+'\n')
