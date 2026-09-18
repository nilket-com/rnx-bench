"""Verify archived source correspondence and run checks without changing installed inputs."""
from pathlib import Path
import subprocess as sp, json,hashlib,os,sys
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/runtime-install-0064';I=Path(json.loads((O/'snapshot.json').read_text())['installed'])
base=json.loads((O/'import.json').read_text())['baseline'];changed={'tools/project/src/main.rs','tools/project/src/workflow/transition.rs','tools/project/src/runtime_probe.rs'}
paths=sp.check_output(['git','-C',str(R),'ls-tree','-r','--name-only',base],text=True).splitlines();hashes={}
for path in paths:
 raw=sp.check_output(['git','-C',str(R),'show',base+':'+path]);hashes[path]=hashlib.sha256(raw).hexdigest()
 if path not in changed:assert (I/path).read_bytes()==raw,path
assert (I/'tools/project/src/runtime_probe.rs').read_bytes()==(H/'runtime_probe.rs').read_bytes()
# Recreate a base tree and prove the checked-in patch applies and yields exactly the installed source.
D=W/'patch-check';D.mkdir();import tarfile
archive=W/'patch-check.tar';sp.run(['git','-C',str(R),'archive','--format=tar','-o',str(archive),base],check=True)
with tarfile.open(archive) as t:t.extractall(D,filter='data')
archive.unlink();sp.run(['git','init','-q','--template='],cwd=D,check=True);sp.run(['git','apply','--check',str(H/'prototype.patch')],cwd=D,check=True);sp.run(['git','apply',str(H/'prototype.patch')],cwd=D,check=True)
for path in paths+['tools/project/src/runtime_probe.rs']:assert (D/path).read_bytes()==(I/path).read_bytes(),path
(O/'source-correspondence.json').write_text(json.dumps({'baseline':base,'unchanged_files':len(paths)-2,'modified':sorted(changed),'baseline_file_sha256':hashes,'patch_reconstructs_installed_tree':True,'fingerprinter_inventory_generator_identity_and_all_root_code_unchanged':True,'binaries':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (W/'bin').iterdir()}},indent=2)+'\n')
m=I/'tools/project/Cargo.toml'
support_only = '--support-only' in sys.argv
with (O/'tool-checks.log').open('a' if support_only else 'w') as log:
 for features in ([['--features','test-support']] if support_only else [[],['--features','test-support']]):
  for action in ['clippy','test']:
   cmd=['cargo',action,'--manifest-path',str(m),'--locked','--offline','--all-targets','--target-dir',str(W/'tool-check'),*features]
   if action=='clippy':cmd+=['--','-D','warnings']
   log.write('COMMAND '+repr(cmd)+'\n');log.flush();sp.run(cmd,stdout=log,stderr=sp.STDOUT,check=True)
 sp.run(['cargo','fmt','--manifest-path',str(m),'--check'],stdout=log,stderr=sp.STDOUT,check=True)
print('PASS exact source correspondence, tool fmt/clippy/tests in both configurations')
