from pathlib import Path
import subprocess as sp,sys
H=Path(__file__).resolve().parent
for name,args in [('freeze.py',[]),('stress.py',[]),('scope.py',[]),('replay.py',['contracts']),('supplement.py',[]),('installed.py',[])]:
 sp.run([sys.executable,str(H/name),*args],check=True)
