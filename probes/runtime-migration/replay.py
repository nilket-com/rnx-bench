from pathlib import Path
import subprocess as sp,json,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];O=B/'results/runtime-migration-0065/publication';O.mkdir(exist_ok=True)
p=B/'probes/runtime-publication/check.py';s=p.read_text().replace("H=Path(__file__).resolve().parent;B=H.parents[1]",f"H=Path({str(H)!r});B=Path({str(B)!r})").replace("W=H/'target'","W=H/'target/publication'").replace("O=B/'results/runtime-publication-0064'","O=B/'results/runtime-migration-0065/publication'").replace("tool_sha256='x'","tool_blake3='x'")
script=O/'check.py';script.write_text(s)
with (O/'replay.log').open('w') as f:sp.run(['python3',script],stdout=f,stderr=sp.STDOUT,check=True)
(O/'adaptation.json').write_text(json.dumps(dict(original='probes/runtime-publication/check.py',sha256=hashlib.sha256(p.read_bytes()).hexdigest(),changes=['isolated target/results','bad tool digest uses current tool_blake3 field']),indent=2)+'\n')
print('PASS current installer publication regression')
