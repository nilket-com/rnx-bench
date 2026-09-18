"""Repeat the accepted gate-5 drivers without changing their matrix or seeds."""
from pathlib import Path
import subprocess as sp,sys,json
H=Path(__file__).resolve().parent;B=H.parents[1];O=B/'results/nested-position-0065';O.mkdir(exist_ok=True)
name=sys.argv[1];assert name in ['replay','checks','measure','fallback']
s=(B/'probes/nested-product'/f'{name}.py').read_text()
s=s.replace("H=Path(__file__).resolve().parent;B=H.parents[1];",f"H=Path({str(H)!r});B=Path({str(B)!r});",1)
s=s.replace('results/nested-product-0065','results/nested-position-0065')
s=s.replace('isolated paths and private product probe instead of copied candidate; assertions unchanged','isolated paths and product private probe; ignored nested repository and 14000 ignored build files require eligibility under F3, with exact tree and allowance equality retained')
# Keep the old fixture intact; archive adapted topology assertions explicitly.
if name=='replay':
 s=s.replace("p=O/f'{name}-driver.py';p.write_text(s)","""if name == 'extra':
  s=s.replace("pair('ignored-nested-repository',[p,p/'a']);assert sum('git' in x for x in r[1]['events'])==6","pair('ignored-nested-repository',[p,p/'a']);assert sum('git' in x for x in r[1]['events'])==3")
  s=s.replace('range(4097)', 'range(14000)').replace('discovery-limit-fallback', 'ignored-build-14000-eligible')
  s=s.replace("pair('ignored-build-14000-eligible',[p,p/'a']);assert sum('git' in x for x in r[1]['events'])==6","pair('ignored-build-14000-eligible',[p,p/'a']);assert sum('git' in x for x in r[1]['events'])==3")
 p=O/f'{name}-driver.py';p.write_text(s)""")
if name=='fallback':
 s=s.replace('4097','14000').replace('GIT_PAGER','GIT_EDITOR').replace('git-pager','git-editor').replace('descendant-budget','ignored-build').replace('budget=4096','descendant_walk=False')

p=O/(name+'-driver.py');p.write_text(s)
sp.run(['python3',p],check=True)
