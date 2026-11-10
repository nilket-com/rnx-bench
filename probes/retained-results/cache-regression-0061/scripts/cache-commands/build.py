"""Build frozen legacy commands, then current commands, with separate target directories."""
from pathlib import Path
import io,shutil,subprocess,tarfile
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/cache-regression-0061/commands';D=H/'target/legacy-source';D.mkdir(parents=True,exist_ok=True);O.mkdir(exist_ok=True)
data=subprocess.check_output(['git','-C',R,'archive','814d20f','tools/project','rustfmt.toml'])
with tarfile.open(fileobj=io.BytesIO(data)) as archive:archive.extractall(D,filter='data')
legacy_target=H/'target/legacy-build';legacy_target.mkdir(exist_ok=True)
if not (legacy_target/'debug').exists():subprocess.run(['cp','-a','--reflink=auto',R/'tools/project/target/debug',legacy_target/'debug'],check=True)
for name,manifest in [('legacy',D/'tools/project/Cargo.toml'),('current',R/'tools/project/Cargo.toml')]:
 target=legacy_target if name=='legacy' else R/'tools/project/target'
 if name=='current':subprocess.run(['cargo','clean','--manifest-path',manifest,'--target-dir',target,'-p','rnx-project'],check=True)
 with (O/(name+'-build.log')).open('w') as f:subprocess.run(['cargo','build','--locked','--offline','--manifest-path',manifest,'--target-dir',target,'--features','test-support','--bin','rnx-project'],stdout=f,stderr=subprocess.STDOUT,check=True)
 if name=='legacy':shutil.copy2(target/'debug/rnx-project',H/'target/legacy-tool')
print('built legacy 814d20f and current test-support commands')
