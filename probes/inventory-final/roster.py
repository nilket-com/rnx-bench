"""Keep the accepted real stale-target and Git-variable eligibility controls."""
from pathlib import Path
import subprocess as sp,sys
H=Path(__file__).resolve().parent;B=H.parents[1];O=B/'results/inventory-final-0065/roster';O.mkdir(exist_ok=True)
p=B/'probes/nested-position/roster.py';s=p.read_text().replace('H=Path(__file__).resolve().parent;B=H.parents[1];',f'H=Path({str(H)!r});B=Path({str(B)!r});',1).replace("O=B/'results/nested-position-0065'",f"O=Path({str(O)!r})");dest=O/'driver.py';dest.write_text(s);sp.run([sys.executable,dest],check=True)
