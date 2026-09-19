"""Retain real clean and dirty coordinate builds independently of root status."""
from pathlib import Path
import subprocess as sp,shutil,json
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/stock-management-0067';S=W/'clean-source'
assert not sp.check_output(['git','status','--porcelain'],cwd=S)
shutil.copy2(S/'target/debug/rnx',W/'clean-rnx')
p=S/'README.md';before=p.read_bytes()
try:
 p.write_bytes(before+b'\nDirty-coordinate fixture.\n')
 with (O/'dirty-build.log').open('w') as f:sp.run(['cargo','build','--locked','--offline','--features','test-support','--bin','rnx'],cwd=S,stdout=f,stderr=sp.STDOUT,check=True)
 shutil.copy2(S/'target/debug/rnx',W/'dirty-rnx')
finally:p.write_bytes(before)
# Return the fixture's regular executable to the clean build too.
with (O/'clean-restore-build.log').open('w') as f:sp.run(['cargo','build','--locked','--offline','--features','test-support','--bin','rnx'],cwd=S,stdout=f,stderr=sp.STDOUT,check=True)
