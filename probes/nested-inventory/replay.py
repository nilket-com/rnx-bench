from pathlib import Path
import subprocess as sp
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/nested-inventory-0065/migration';O.mkdir(exist_ok=True)
s=(B/'probes/runtime-migration/check.py').read_text()
s=s.replace("H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target/matrix';O=B/'results/runtime-migration-0065';",f"H=Path({str(H)!r});B=Path({str(B)!r});R=B.parent/'rnx';W=H/'target/migration';O=Path({str(O)!r});")
s=s.replace("l.startswith('rnx-project runtime install')", "' runtime install --from ' in l").replace("shlex.split(line)==['rnx-project','runtime'", "shlex.split(line)==[str(T),'runtime'")
f=O/'check.py';f.write_text(s)
with (O/'build.log').open('w') as log:sp.run(['cargo','build','--locked','--offline','--manifest-path',R/'tools/project/Cargo.toml','--features','test-support','--bin','rnx-project'],stdout=log,stderr=sp.STDOUT,check=True)
with (O/'matrix.log').open('w') as log:sp.run(['python3',f],stdout=log,stderr=sp.STDOUT,check=True)
print('PASS 30-case migration replay with absolute recovery expectation')
