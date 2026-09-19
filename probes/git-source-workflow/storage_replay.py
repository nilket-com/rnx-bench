"""Unchanged authentic legacy migration and removal matrices, new product frontend."""
from common import *
import sys,tarfile,io,shutil
phase=sys.argv[1]
D=T/('storage-'+phase);D.mkdir();out=O/('storage-'+phase);out.mkdir()
if phase=='migration':
 old=D/'old';old.mkdir();archive=git(R,'archive','7cd3205','tools/project','rustfmt.toml').stdout
 with tarfile.open(fileobj=io.BytesIO(archive)) as a:a.extractall(old,filter='data')
 r=run(['cargo','build','--locked','--offline','--manifest-path',old/'tools/project/Cargo.toml','--bin','rnx-project']);(out/'old-build.log').write_bytes(r.stderr)
 file=B/'probes/runtime-migration/check.py';s=file.read_text().replace("W=H/'target/matrix'",'W=Path('+repr(str(D/'matrix'))+')').replace("O=B/'results/runtime-migration-0065'",'O=Path('+repr(str(out))+')').replace("OLD=B/'probes/native-inventory/target/stock/tools/project/target/release/rnx-project'",'OLD=Path('+repr(str(old/'tools/project/target/debug/rnx-project'))+')')
 s=s.replace("T=R/'tools/project/target/debug/rnx-project'",'T=Path('+repr(str(TOOL))+')')
else:
 assert phase=='removal'
 file=B/'probes/removal-commands/filesystem.py';s=file.read_text().replace("P=H/'target/bin/rnx-project-support'",'P=Path('+repr(str(TOOL))+')').replace("W=H/'target/cases'",'W=Path('+repr(str(D/'cases'))+')').replace("B/'results/removal-commands-0066'",'Path('+repr(str(out))+')')
if phase=='migration':
 s=s.replace("l.startswith('rnx-project runtime install')", "' runtime install --from ' in l")
 s=s.replace("['rnx-project','runtime','install','--from',str(entry/'source')]", "[str(T),'runtime','install','--from',str(entry/'source')]")
script=out/'effective.py' ;script.write_text(s);save('storage-'+phase+'-adaptation.json',{'original':str(file.relative_to(B)),'original_sha256':sha(file.read_bytes()),'effective_sha256':sha(s.encode()),'old_commit':'7cd3205' if phase=='migration' else None})
loader='import sys;sys.dont_write_bytecode=True;exec(compile(open(sys.argv[1]).read(),sys.argv[2],"exec"),{"__name__":"__main__","__file__":sys.argv[2]})'
r=run([sys.executable,'-c',loader,script,file],ok=False);(out/'replay.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stderr.decode();print(phase,'matrix passes',flush=True)
