"""Replay existing current-format workflow, publication, migration and interactive gates."""
from pathlib import Path
import json,subprocess as sp,sys,hashlib,time
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/inventory-final-0065';rows=[]
def run(source,group,old_result,adjust=lambda s:s):
 p=B/'probes'/source;raw=p.read_text();h=W/group;h.mkdir(exist_ok=True);out=O/group;out.mkdir(exist_ok=True)
 s=raw.replace('H=Path(__file__).resolve().parent;B=H.parents[1]',f'H=Path({str(h)!r});B=Path({str(B)!r})',1)
 s=s.replace('results/'+old_result,'results/inventory-final-0065/'+group)
 s=adjust(s)
 if group=='recovery':(h/'target').mkdir(exist_ok=True)
 dest=out/'replay.py';dest.write_text(s);start=time.monotonic()
 loader='import sys;sys.dont_write_bytecode=True;exec(compile(open(sys.argv[1]).read(),sys.argv[2],"exec"),{"__name__":"__main__","__file__":sys.argv[2]})'
 with (out/'replay.log').open('w') as f:p2=sp.run([sys.executable,'-c',loader,dest,p],stdout=f,stderr=sp.STDOUT,timeout=1200)
 rows.append(dict(source=source,source_sha256=hashlib.sha256(raw.encode()).hexdigest(),effective_sha256=hashlib.sha256(s.encode()).hexdigest(),group=group,status=p2.returncode,seconds=time.monotonic()-start));(O/'supplement.json').write_text(json.dumps(rows,indent=2)+'\n');assert p2.returncode==0,group;print('PASS supplement',group,flush=True)
run('inventory-workflow/contracts.py','workflow','inventory-workflow-0065')
run('inventory-workflow/publication.py','cache-publication','inventory-workflow-0065')
run('nested-inventory/replay.py','migration','nested-inventory-0065')
run('nested-inventory/recovery.py','recovery','nested-inventory-0065')
def interactive(s):
 s=s.replace("B=pathlib.Path(__file__).resolve().parents[2]",f"B=pathlib.Path({str(B)!r})")
 s=s.replace("root=pathlib.Path(tmp);", "root=pathlib.Path(tmp);ENV['RNX_PROJECT_CACHE']=str(root/'cache');")
 s=s.replace("artifact=app/'.rnx/artifacts'/r['executable_sha256']", "artifact=root/'cache/entries'/r['assembly_key']/'artifacts'/r['executable_blake3']")
 s=s.replace("run('lock',['--offline']);assert run('session')[1]==size", "run('lock',['--offline']);run('build');assert run('session')[1]==0")
 s=s.replace("receipt.write_text(json.dumps(old));assert run(mode,tail)[1]==size;assert run(mode,tail)[1]==0", "receipt.write_text(json.dumps(old));saved=receipt.read_bytes();run(mode,tail,False);assert receipt.read_bytes()==saved;run('build');assert run(mode,tail)[1]==0")
 s=s.replace("else:assert run(mode,tail)[1]==size", "else:run(mode,tail,False);run('build');assert run(mode,tail)[1]==0")
 s=s.replace("bad['lock_sha256']", "bad['lock_blake3']")
 return s
run('project-interactive/contracts.py','interactive','project-interactive-0060',interactive)
print('PASS current-format supplements')
