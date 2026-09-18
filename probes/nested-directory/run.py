"""Repeat the accepted gate-5 drivers without changing their matrix or seeds."""
from pathlib import Path
import subprocess as sp,sys,json
H=Path(__file__).resolve().parent;B=H.parents[1];O=B/'results/nested-directory-0065';O.mkdir(exist_ok=True)
name=sys.argv[1];assert name in ['replay','checks','measure','fallback']
s=(B/'probes/nested-product'/f'{name}.py').read_text()
s=s.replace("H=Path(__file__).resolve().parent;B=H.parents[1];",f"H=Path({str(H)!r});B=Path({str(B)!r});",1)
s=s.replace('results/nested-product-0065','results/nested-directory-0065')
# checks.py computes paths differently; only its output path changes.
p=O/(name+'-driver.py');p.write_text(s)
sp.run(['python3',p],check=True)
