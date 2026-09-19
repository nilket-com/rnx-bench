"""Replay the accepted product filesystem/contracts against final frozen binaries."""
from pathlib import Path
import subprocess as sp,sys,json,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/removal-final-0066';rows=[]
for name in ['filesystem','contracts']:
 original=B/'probes/removal-commands'/(name+'.py');raw=original.read_text();local=W/('removal-'+name);local.mkdir();out=O/('removal-'+name);out.mkdir()
 s=raw.replace('H=Path(__file__).resolve().parent;B=H.parents[1]',f'H=Path({str(local)!r});B=Path({str(B)!r})').replace('H=Path(__file__).resolve().parent; B=H.parents[1]',f'H=Path({str(local)!r}); B=Path({str(B)!r})')
 s=s.replace("H/'target/bin/rnx-project-support'",'Path('+repr(str(W/'tool-support'))+')').replace("H/'target/bin/rnx-project-ordinary'",'Path('+repr(str(W/'tool-ordinary'))+')')
 s=s.replace("H/'templates/old'",'Path('+repr(str(B/'probes/removal-commands/templates/old'))+')').replace("H/'templates/new'",'Path('+repr(str(B/'probes/removal-commands/templates/new'))+')')
 s=s.replace('results/removal-commands-0066','results/removal-final-0066/removal-'+name)
 script=out/'driver.py';script.write_text(s)
 with (out/'run.log').open('w') as f:p=sp.run([sys.executable,script],stdout=f,stderr=sp.STDOUT)
 rows.append(dict(driver=name,original_sha256=hashlib.sha256(raw.encode()).hexdigest(),status=p.returncode));assert p.returncode==0,(out/'run.log').read_text()
(O/'removal-replay.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS final filesystem and contract replay')
