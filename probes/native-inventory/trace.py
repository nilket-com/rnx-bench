"""Untimed process control for the Git intervals; no contribution to sample medians."""
from pathlib import Path
import subprocess as sp,json,platform
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/native-inventory-0065';e=json.loads((W/'env.json').read_text())
cmd=['strace','-f','-qq','-s','1024','-e','trace=process','-o',str(O/'git-process.trace'),str(W/'stock/tools/project/target/release/inventory-probe'),str(W/'shallow-3.json')]
r=sp.run(cmd,env=e,capture_output=True,text=True,check=True);assert r.stdout=='42\n'
lines=(O/'git-process.trace').read_text().splitlines();classes={}
for name,needle in [('submodule','"rev-parse"'),('untracked','"--others"'),('tracked','"--stage"'),('nested_parent_listing','"--literal-pathspecs"')]:
 classes[name]=sorted({int(s.split()[0]) for s in lines if 'execve(' in s and needle in s})
classes['tracked']=sorted(set(classes['tracked'])-set(classes['nested_parent_listing']))
assert all(len(v)==4 for v in classes.values()),classes
(O/'git-process-control.json').write_text(json.dumps(dict(command=cmd,stdout=r.stdout,stderr=r.stderr,scope='one untimed diagnostic run outside journal; four native trees share one Git working tree nested under bench',git_process_pids=classes),indent=2)+'\n')
info={}
for line in Path('/proc/cpuinfo').read_text().splitlines():
 if line.startswith('model name'):info['cpu_model']=line.split(':',1)[1].strip();break
info.update(platform=platform.platform(),rustc=sp.check_output(['rustc','-Vv'],text=True),git=sp.check_output(['git','--version'],text=True).strip())
(O/'host.json').write_text(json.dumps(info,indent=2)+'\n')
print('PASS four submodule commands, eight listings and four nested Git children')
