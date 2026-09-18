"""Repeat the identical 4500-sample gate matrix; never overwrite the accepted miss."""
from pathlib import Path
import subprocess as sp,sys
H=Path(__file__).resolve().parent;B=H.parents[1];O=B/'results/inventory-final-0065/headline';O.mkdir(exist_ok=True)
p=B/'probes/nested-product/measure.py';s=p.read_text().replace('H=Path(__file__).resolve().parent;B=H.parents[1];',f'H=Path({str(H)!r});B=Path({str(B)!r});',1).replace('results/nested-product-0065','results/inventory-final-0065/headline');dest=O/'measure-driver.py';dest.write_text(s)
sp.run([sys.executable,dest],check=True)
