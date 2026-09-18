"""Pre-launch restored-mtime edits refuse in both modes of isolated integration."""
from pathlib import Path
import os,json,subprocess as sp,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];T=H/'target/tool/tools/project/target/release/rnx-project';O=B/'results/nested-inventory-0065'
setup=json.loads((B/'results/inventory-workflow-0065/setup.json').read_text());row=next(r for r in setup if r['count']==2);m=Path(row['current']['manifest']);root=Path(row['trees'][0]['root']);f=root/'adapters/postgres/src/lib.rs';raw=f.read_bytes();st=f.stat();assert raw
E=json.loads((B/'probes/inventory-workflow/target/env.json').read_text());E={k:v for k,v in E.items() if not k.startswith(('GIT_','NESTED_'))}
protected=[m.parent/'rnx.lock',m.parent/'rnx.Cargo.lock',m.parent/'.rnx/receipt.json'];before={str(p):p.read_bytes() for p in protected};results=[]
def call(verify,ok):
 args=[str(T),'eval','--manifest',str(m)]+(['--verify'] if verify else [])+['--','42'];p=sp.run(args,env=E,capture_output=True,text=True,timeout=60);assert (p.returncode==0)==ok,(args,p.stdout,p.stderr)
 if ok:assert p.stdout=='42\n'
 else:assert 'native' in p.stderr.lower() or 'source' in p.stderr.lower(),p.stderr
 results.append(dict(verify=verify,expected_success=ok,status=p.returncode,stdout=p.stdout,stderr=p.stderr))
try:
 call(False,True);call(True,True)
 # Equal size, same inode/mode, restored timestamp; content verification must win.
 f.write_bytes(bytes([raw[0]^1])+raw[1:]);os.utime(f,ns=(st.st_atime_ns,st.st_mtime_ns));assert f.stat().st_size==st.st_size
 call(False,False);call(True,False)
finally:
 f.write_bytes(raw);os.utime(f,ns=(st.st_atime_ns,st.st_mtime_ns))
call(False,True)
assert {str(p):p.read_bytes() for p in protected}==before
(O/'launch.json').write_text(json.dumps(dict(cases=results,files_restored=True,lock_pair_receipt_unchanged=True,tool_sha256=hashlib.sha256(T.read_bytes()).hexdigest()),indent=2)+'\n')
print('PASS candidate real launch, both restored-mtime refusals, restored inputs launch')
