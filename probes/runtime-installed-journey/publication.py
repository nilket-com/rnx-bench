"""Replay accepted gate 2 verbatim, redirecting only target/results."""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;B=H.parents[1]
p=B/'probes/runtime-publication/check.py';raw=p.read_text()
s=raw.replace("W=H/'target';O=B/'results/runtime-publication-0064'", "W=B/'probes/runtime-installed-journey/target/publication';O=B/'results/runtime-installed-journey-0064/publication'")
assert s!=raw
out=B/'results/runtime-installed-journey-0064';out.mkdir(exist_ok=True)
(out/'publication-driver.json').write_text(json.dumps(dict(original=str(p),sha256=hashlib.sha256(raw.encode()).hexdigest(),change='only W/O redirected to gate 4 evidence and ignored target'),indent=2)+'\n')
exec(compile(s,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
