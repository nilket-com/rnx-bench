from common import *
import sys
H=T/'publication-replay';H.mkdir();out=O/'publication-replay';out.mkdir()
p=B/'probes/cache-publication/publication_probe.rs';s=p.read_text().replace('use sha2::{Digest, Sha256};','mod schemas;\nmod new_identity;\nmod git_inventory;').replace('format!("{:x}", Sha256::digest(&bytes)) != file.sha256','blake3::hash(&bytes).to_hex().as_str() != file.blake3');(H/'publication_probe.rs').write_text(s)
for name in ['build.py','check.py']:
 p=B/'probes/cache-publication'/name;s=p.read_text().replace("H=Path(__file__).resolve().parent;B=H.parents[1]",f"H=Path({str(H)!r});B=Path({str(B)!r})").replace("O=B/'results/cache-publication-0061'",'O=Path('+repr(str(out))+')')
 s=s.replace('project-sources=[]', 'project-sources=[]\\ncount-allocations=[]')
 script=out/name;script.write_text(s)
 r=run([sys.executable,script],ok=False);(out/(name+'.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stderr.decode()
save('publication-replay-adaptation.json',{'source':'probes/cache-publication','changes':['isolated output paths','BLAKE3 audit helper','declare new private schema/identity/Git modules required by current publisher','stub runtime declares count-allocations required since gate 2'],'probe_sha256':sha((H/'publication_probe.rs').read_bytes())})
print('37-case original publication matrix passes',flush=True)
