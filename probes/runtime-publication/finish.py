"""Ordinary build smoke, full snapshot install, source archive and legacy workflow replay."""
from pathlib import Path
import subprocess as sp,os,json,hashlib,shutil,tempfile
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'full';O=B/'results/runtime-publication-0064'
# Required before the full-source fingerprint: new implementation files must be staged.
assert not sp.check_output(['git','-C',str(R),'ls-files','--others','--exclude-standard'])
with (O/'ordinary-build.log').open('w') as log:sp.run(['cargo','build','--manifest-path',str(R/'tools/project/Cargo.toml'),'--release','--locked','--offline'],stdout=log,stderr=sp.STDOUT,check=True)
W.mkdir(exist_ok=True);T=W/'ordinary-tool';shutil.copy2(R/'tools/project/target/release/rnx-project',T)
# Each invocation uses a fresh store, even if finish is repeated after a source correction.
data=Path(tempfile.mkdtemp(prefix='data-',dir=W));e={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','RNX_'))};e.update(XDG_DATA_HOME=str(data),RNX_PROJECT_CACHE=str(W/'cache'),XDG_STATE_HOME=str(W/'state'),RNX_INSTALL_FAIL='before-entry-rename',RNX_INSTALL_SOURCE_BYTES='1')
args=[str(T),'runtime','install','--from',str(R)];p=sp.run(args,env=e,capture_output=True,text=True);(O/'full-install.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
root=data/'rnx/runtimes';id=json.loads((root/'current.json').read_text())['id'];entry=root/'entries'/id
before={str(p.relative_to(entry)):(p.stat().st_ino,p.stat().st_mtime_ns,hashlib.sha256(p.read_bytes()).hexdigest()) for p in entry.rglob('*') if p.is_file()}
p=sp.run(args,env=e,capture_output=True,text=True);assert p.returncode==0,p.stderr
assert before=={str(p.relative_to(entry)):(p.stat().st_ino,p.stat().st_mtime_ns,hashlib.sha256(p.read_bytes()).hexdigest()) for p in entry.rglob('*') if p.is_file()}
(O/'full-install.json').write_text(json.dumps({'installation':json.loads((entry/'installation.json').read_text()),'all_shipped_layouts_pass':True,'second_install_byte_inode_mtime_noop':True,'ordinary_ignores_test_failures_and_limits':True},indent=2)+'\n')
patch=sp.check_output(['git','-C',str(R),'diff','--no-color','--binary','HEAD','--','tools/project']);(O/'measured-tool.patch').write_bytes(patch)
(O/'source.json').write_text(json.dumps({'base':sp.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip(),'patch_sha256':hashlib.sha256(patch).hexdigest(),'ordinary_tool_sha256':hashlib.sha256(T.read_bytes()).hexdigest(),'support_tool_sha256':hashlib.sha256((H/'target/rnx-project').read_bytes()).hexdigest(),'tool_files':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'tools/project/src').rglob('*.rs')}},indent=2)+'\n')
# Replay the existing 13-group real cache/legacy workflow; preserve its published results.
old=B/'results/cache-commands-0061'
with tempfile.TemporaryDirectory(prefix='rnx-0064-saved-results-') as d:
 backup=Path(d)/'old';shutil.copytree(old,backup)
 try:
  # check.py names the normal debug tool, so explicitly build the required hooks first.
  sp.run(['cargo','build','--manifest-path',str(R/'tools/project/Cargo.toml'),'--features','test-support','--locked','--offline'],check=True)
  with (O/'cache-regression.log').open('w') as log:
   p=sp.run(['python3',str(B/'probes/cache-commands/check.py')],cwd=B,stdout=log,stderr=sp.STDOUT);assert p.returncode==0,(O/'cache-regression.log').read_text()
  dest=O/'cache-regression';dest.mkdir(exist_ok=True)
  for name in ['legacy.lock.json','legacy.receipt.json','shared.lock.json','shared.receipt.json','shared.ready.json','Cargo.lock','native-builds.log','runtime','conditions.json','results.json']:
   if (old/name).is_dir():shutil.copytree(old/name,dest/name,dirs_exist_ok=True)
   else:shutil.copy2(old/name,dest/name)
  shutil.copy2(O/'measured-tool.patch',dest/'source.patch')
 finally:shutil.rmtree(old);shutil.copytree(backup,old)
print('PASS ordinary/full-source installation, no-op, source archive and cache regression')
