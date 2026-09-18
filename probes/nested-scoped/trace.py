"""Diagnostic syscalls after timing, including Git's internal child execs."""
from pathlib import Path
import os,json,subprocess as sp,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/nested-scoped-0065';E=json.loads((B/'probes/inventory-workflow/target/env.json').read_text());assert not any(k.startswith('GIT_') for k in E);E.update(POLARS_MAX_THREADS='1',RNX_CONFIG=str(W/'absent'));cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu});projects=json.loads((B/'results/inventory-workflow-0065/setup.json').read_text());rows=[]
for n in [0,1,3]:
 for name,tool in [('format',W/'format'),('F2',B/'probes/nested-directory/target/reuse'),('F3-F4',W/'reuse')]:
  log=O/f'syscalls-{name}-{n}.log';p=sp.run(['strace','-f','-e','trace=statx,execve','-o',str(log),str(tool),'eval','--manifest',projects[n]['current']['manifest'],'--','42'],env=E,capture_output=True,text=True,timeout=30);assert p.returncode==0 and p.stdout=='42\n' and not p.stderr,p.stderr
  lines=log.read_text().splitlines();rows.append(dict(count=n,version=name,tool=str(tool),sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),statx=sum('statx(' in l for l in lines),enoent=sum('statx(' in l and 'ENOENT' in l for l in lines),successful_execs=[l for l in lines if 'execve(' in l and '= 0' in l]))
(O/'syscalls.json').write_text(json.dumps(dict(cpu=cpu,scope='diagnostic counts only; successful execs include tool and final artifact, PATH search failures excluded',rows=rows),indent=2)+'\n');print([(r['version'],r['count'],r['statx'],r['enoent'],len(r['successful_execs'])) for r in rows])
