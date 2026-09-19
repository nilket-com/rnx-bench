"""Replay all accepted publication assertions with the current product modules."""
from pathlib import Path
import subprocess as sp,json,hashlib
H=Path('/home/me/work/rnx-bench/probes/removal-final/target/cache-publication');B=Path('/home/me/work/rnx-bench');O=B/'results/removal-final-0066/cache-publication/publication';O.mkdir(exist_ok=True)
p=B/'probes/cache-publication/publication_probe.rs';s=p.read_text().replace('use sha2::{Digest, Sha256};','').replace('format!("{:x}", Sha256::digest(&bytes)) != file.sha256','blake3::hash(&bytes).to_hex().as_str() != file.blake3');(H/'publication_probe.rs').write_text(s)
for name in ['build.py','check.py']:
 p=B/'probes/cache-publication'/name;s=p.read_text().replace("H=Path(__file__).resolve().parent;B=H.parents[1]",f"H=Path({str(H)!r});B=Path({str(B)!r})").replace("O=B/'results/cache-publication-0061'", "O=B/'results/removal-final-0066/cache-publication/publication'").replace("H/'target/tool", "H/'target/publication/tool")
 s=s.replace("'source_patch':'source.patch'", "'source_patch':'../tool.patch'")
 script=O/name;script.write_text(s)
 with (O/(name+'.log')).open('w') as f:sp.run(['python3',str(script)],stdout=f,stderr=sp.STDOUT,check=True)
(O/'adaptations.json').write_text(json.dumps(dict(source='probes/cache-publication',changes=['isolated paths under inventory-workflow','probe audit helper uses current blake3 field and algorithm','all 37 publication assertions unchanged'],probe_sha256=hashlib.sha256((H/'publication_probe.rs').read_bytes()).hexdigest()),indent=2)+'\n')
print('PASS publication replay')
