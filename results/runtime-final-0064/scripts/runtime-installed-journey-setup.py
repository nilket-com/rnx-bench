"""One exact product snapshot for launcher, tool and installation; no prototype patch."""
from pathlib import Path
import subprocess as sp,os,json,shutil,hashlib,tarfile
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=Path('/home/me/work/rnx-bench/probes/runtime-final/target/installed');O=B/'results/runtime-final-0064/installed';BASE='5198758'
assert not W.exists();W.mkdir();O.mkdir(exist_ok=True);(O/'phases.jsonl').unlink(missing_ok=True);C=W/'original';C.mkdir()
for name in sp.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0'):
 if name:
  d=C/name;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/name,d)
patch=sp.check_output(['git','diff','--no-color','--binary',BASE,'--'],cwd=R);(O/'source.patch').write_bytes(patch)
e={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','RNX_','CARGO_','RUST'))};e.update(GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null')
def run(a):return sp.check_output(list(map(str,a)),env=e,stderr=sp.STDOUT)
run(['git','init','-q',C]);run(['git','-C',C,'add','.']);run(['git','-C',C,'-c','user.name=Fixture','-c','user.email=f@invalid','-c','commit.gpgsign=false','commit','-qm','0064 gate 4 product snapshot'])
(O/'snapshot-build.json').write_text(json.dumps(dict(baseline=BASE,patch_sha256=hashlib.sha256(patch).hexdigest(),fixture_commit=run(['git','-C',C,'rev-parse','HEAD']).decode().strip()),indent=2)+'\n')
# Independent targets; both binaries come from the exact installed snapshot.
jobs=[]
for name,manifest in [('tool',C/'tools/project/Cargo.toml'),('launcher',C/'Cargo.toml')]:
 log=(O/(name+'-build.log')).open('w');p=sp.Popen(['cargo','build','--release','--locked','--offline','--manifest-path',str(manifest),'--target-dir',str(W/(name+'-build'))],env=e,stdout=log,stderr=sp.STDOUT);jobs.append((p,log,name))
for p,log,name in jobs:
 rc=p.wait();log.close();assert rc==0,name
(W/'bin').mkdir();shutil.copy2(W/'tool-build/release/rnx-project',W/'bin/rnx-project');shutil.copy2(W/'launcher-build/release/rnx',W/'bin/rnx')
print('PASS same-snapshot ordinary product builds',flush=True)
