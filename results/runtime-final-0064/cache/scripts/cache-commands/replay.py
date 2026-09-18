"""Replay accepted 0059/0060 assertions on legacy locks with the current launcher.
Only successful lock creation uses the frozen pre-cache tool; build and launch
remain current. The transformation and generated sources are archived.
"""
from pathlib import Path
import subprocess,hashlib,json
H=Path(__file__).resolve().parent;B=H.parents[1];O=B/'results/runtime-final-0064/cache/commands';R=B.parent/'rnx';OLD=H/'target/legacy-tool';records={}
for name,source in [('stamp','project-run-default/contracts.py'),('interactive','project-interactive/contracts.py')]:
 p=B/'probes'/source;s=p.read_text()
 s=s.replace("B=pathlib.Path(__file__).resolve().parents[2]",'B=pathlib.Path('+repr(str(B))+')')
 s=s.replace("O=B/'results/project-run-default-0059'",'O=pathlib.Path('+repr(str(O))+')').replace("O=B/'results/project-interactive-0060'",'O=pathlib.Path('+repr(str(O))+')')
 s=s.replace("[str(T),op,'--manifest'",'[(str('+repr(str(OLD))+') if op=="lock" else str(T)),op,\'--manifest\'')
 s=s.replace("[T,mode,'--manifest'",'[('+repr(str(OLD))+' if mode=="lock" else T),mode,\'--manifest\'')
 script=O/(name+'-replay.py');script.write_text(s)
 with (O/(name+'-replay.log')).open('w') as f:subprocess.run(['python3',script],check=True,stdout=f,stderr=subprocess.STDOUT)
 # Both historical fixtures call their output contracts.json.
 (O/(name+'-contracts.json')).write_bytes((O/'contracts.json').read_bytes());(O/'contracts.json').unlink()
 records[name]={'input':str(p.relative_to(B)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'generated':script.name,'scope':'legacy lock seeded by frozen tool; all builds and launches use new tool'}
(O/'replays.json').write_text(json.dumps(records,indent=2)+'\n');print('PASS legacy 0059 and 0060 contract replays')
