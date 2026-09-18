"""Build an isolated tool/launcher from one fixture snapshot, never the working checkout."""
from pathlib import Path
import subprocess as sp, os, json, hashlib, shutil, tarfile
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/runtime-install-0064'
BASE='b4510d4'
def run(a,**kw):return sp.run(list(map(str,a)),check=True,**kw)
def cleanenv():
 e={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
 e.update(GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1',GIT_ATTR_NOSYSTEM='1');return e
if W.exists():raise SystemExit('fresh target required')
W.mkdir();O.mkdir(exist_ok=True);C=W/'original';C.mkdir()
archive=W/'source.tar';run(['git','-C',R,'archive','--format=tar','-o',archive,BASE])
with tarfile.open(archive) as t:t.extractall(C,filter='data')
archive.unlink()
P=C/'tools/project';main=P/'src/main.rs';transition=P/'src/workflow/transition.rs'
original={str(p.relative_to(C)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [main,transition]}
main.write_text(main.read_text().replace('mod workflow;','mod workflow;\nmod runtime_probe;').replace('if let Err(error) = workflow::cli(std::env::args_os().skip(1).collect()) {','let args: Vec<_> = std::env::args_os().skip(1).collect();\n\tlet result = if args.first().is_some_and(|v| v == "runtime-probe") { runtime_probe::cli(&args[1..]) } else { workflow::cli(args) };\n\tif let Err(error) = result {'))
s=transition.read_text().replace('struct Description {','struct Description {\n\truntime_notice: String,')
s=s.replace('if self.candidate.added.iter().any(|n| n == "polars") {','if !self.runtime_notice.is_empty() { notice.push_str(&self.runtime_notice); notice.push(\'\\n\'); }\n\t\tif self.candidate.added.iter().any(|n| n == "polars") {')
s=s.replace('let (manifest, original) = if scratch {','let mut runtime_notice = String::new();\n\tlet (manifest, original) = if scratch {')
start=s.index('\t\tlet runtime = PathBuf::from(',s.index('fn describe('));end=s.index('\t\tlet selected = scratch_path()?;',start)
s=s[:start]+'\t\tlet (runtime, notice) = crate::runtime_probe::selection()?;\n\t\truntime_notice = notice;\n'+s[end:]
s=s.replace('Ok(Description {','Ok(Description {\n\truntime_notice,').replace('create_scratch(&fresh)?;','crate::runtime_probe::validate_selected()?;\n\t\t\tcreate_scratch(&fresh)?;');transition.write_text(s)
shutil.copy2(H/'runtime_probe.rs',P/'src/runtime_probe.rs')
run(['cargo','fmt','--manifest-path',P/'Cargo.toml']);shutil.copy2(P/'src/runtime_probe.rs',H/'runtime_probe.rs')
# Archive a normal, colour-free patch against the imported snapshot, including the new file.
e=cleanenv();run(['git','-C',C,'init','-q','--template='],env=e)
# Generate patch with a disposable base index before staging the final fixture snapshot.
run(['git','-C',R,'archive','--format=tar','-o',W/'base.tar',BASE]);D=W/'patch-base';D.mkdir()
with tarfile.open(W/'base.tar') as t:t.extractall(D,filter='data')
(W/'base.tar').unlink();run(['git','-C',D,'init','-q','--template='],env=e);run(['git','-C',D,'add','.'],env=e)
for rel in ['tools/project/src/main.rs','tools/project/src/workflow/transition.rs','tools/project/src/runtime_probe.rs']:
 shutil.copy2(C/rel,D/rel)
run(['git','-C',D,'add','-N','tools/project/src/runtime_probe.rs'],env=e)
patch=sp.check_output(['git','-C',str(D),'diff','--no-color','--binary'],env=e);(H/'prototype.patch').write_bytes(patch)
# The fixture source, launcher and tool all come from this single committed snapshot.
run(['git','-C',C,'add','.'],env=e)
run(['git','-C',C,'-c','user.name=Runtime fixture','-c','user.email=fixture@invalid','-c','commit.gpgsign=false','commit','-qm','isolated 0064 gate 1 fixture'],env=e)
(O/'import.json').write_text(json.dumps({'baseline':sp.check_output(['git','-C',str(R),'rev-parse',BASE],text=True).strip(),'imported':original,'patch_sha256':hashlib.sha256(patch).hexdigest(),'fixture_commit':sp.check_output(['git','-C',str(C),'rev-parse','HEAD'],text=True).strip()},indent=2)+'\n')
# Builds go outside the snapshot. Logs retained; targets start empty.
jobs=[]
for label,manifest,target,extra in [('tool',P/'Cargo.toml',W/'tool-build',[]),('launcher',C/'Cargo.toml',W/'launcher-build',[])]:
 log=(O/(label+'-build.log')).open('w');proc=sp.Popen(['cargo','build','--release','--locked','--offline','--manifest-path',str(manifest),'--target-dir',str(target),*extra],stdout=log,stderr=sp.STDOUT);jobs.append((proc,log,label))
for p,log,label in jobs:
 code=p.wait();log.close()
 if code:raise SystemExit(f'{label} build failed ({code}); see log')
(W/'bin').mkdir();shutil.copy2(W/'tool-build/release/rnx-project',W/'bin/rnx-project');shutil.copy2(W/'launcher-build/release/rnx',W/'bin/rnx')
print('PASS isolated builds',flush=True)
