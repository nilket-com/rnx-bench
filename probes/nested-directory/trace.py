"""Diagnostic syscall counts only; strace times are not launch measurements."""
from pathlib import Path
import os,json,subprocess as sp,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/nested-directory-0065'
E=json.loads((B/'probes/inventory-workflow/target/env.json').read_text());assert not any(k.startswith('GIT_') for k in E);E.update(POLARS_MAX_THREADS='1',RNX_CONFIG=str(W/'absent'))
row=json.loads((B/'results/inventory-workflow-0065/setup.json').read_text())[1];manifest=row['current']['manifest'];cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu});rows=[]
for name,tool in [('format',W/'format'),('stopped',B/'probes/nested-product/target/reuse'),('directory',W/'reuse')]:
 log=O/('statx-'+name+'.log');args=[str(tool),'eval','--manifest',manifest,'--','42'];p=sp.run(['strace','-f','-e','trace=statx','-o',str(log),*args],env=E,capture_output=True,text=True,timeout=30);assert p.returncode==0 and p.stdout=='42\n',p.stderr
 lines=log.read_text().splitlines();calls=[l for l in lines if 'statx(' in l];rows.append(dict(version=name,tool=str(tool),sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),statx=len(calls),enoent=sum('ENOENT' in l for l in lines)))
(O/'statx.json').write_text(json.dumps(dict(cpu=cpu,scope='one-native eval; syscall counts, not timing attribution',rows=rows),indent=2)+'\n');print(rows,flush=True)
