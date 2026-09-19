from common import *
import re,gzip
rows=json.loads((O/'roster.json').read_text());env=json.loads((O/'roster-env.json').read_text());results=[]
traps=T/'traps';traps.mkdir();log=T/'compilation-trap';log.write_text('')
for name in ['cargo','rustc']:
 actual=shutil.which(name,path=env['PATH']);p=traps/name;p.write_text('#!/usr/bin/python3\nimport os,sys\na=sys.argv[1:]\nc=("build" in a or "rustc" in a) if '+repr(name)+'=="cargo" else ("--crate-name" in a and not any(x.startswith("--print") for x in a))\nif c:\n open('+repr(str(log))+',"a").write("trapped\\n")\n sys.exit(91)\nos.execv('+repr(actual)+',['+repr(actual)+',*a])\n');p.chmod(0o700)
trapped=env|{'PATH':str(traps)+':'+env['PATH']}
for args in [['cargo','build'],['rustc','--crate-name','control']]:assert run(args,env=trapped,ok=False).returncode==91
log.write_text('')
for row in rows:
 m=Path(row['manifest']);trace=O/f'trace-{row["kind"]}-{row["count"]}.txt'
 p=run(['strace','-f','-qq','-o',trace,'-e','trace=execve,openat,connect',T/'stock','project','eval','--manifest',m,'--','42'],env=env);assert p.stdout==b'42\n'
 text=trace.read_text();execs=[line for line in text.splitlines() if 'execve(' in line and '= 0' in line]
 if row['kind']=='git':
  lock=json.loads(m.with_name('rnx.lock').read_text());roots={x['checkout'] for x in lock['git']}
  assert len(execs)==2,execs;assert not any('openat(' in line and any(root+'/' in line for root in roots) for line in text.splitlines());assert 'AF_INET' not in text
 else:roots=set()
 # Attachment must hit ready without compilation; controls prove traps are live.
 p=run([T/'stock','project','build','--offline','--manifest',m],env=trapped);assert not log.read_text()
 results.append({'kind':row['kind'],'count':row['count'],'execs':execs,'git_source_roots':sorted(roots),'git_source_opens':0 if row['kind']=='git' else None,'network':False if row['kind']=='git' else None,'attachment_compilation_trapped':True,'trace_sha256':sha(trace)})
 trace.with_suffix('.txt.gz').write_bytes(gzip.compress(trace.read_bytes(),mtime=0));trace.unlink()
save('traces.json',results);print('launch discipline and attachment traps passed',flush=True)
