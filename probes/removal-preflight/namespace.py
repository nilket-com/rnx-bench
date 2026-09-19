"""Mount controls only, always inside a demonstrably separate mount namespace."""
from pathlib import Path
import json, os, subprocess as sp, sys
root=Path(sys.argv[1]); parent_namespace=sys.argv[2]
assert os.readlink('/proc/self/ns/mnt') != parent_namespace, 'refuse host mount namespace'
assert os.geteuid()==0, 'expected mapped namespace root'
(root/'child-entered').write_text('isolated mount namespace\n')
mount=sys.argv[3]
sp.run([mount,'--make-rprivate','/'],check=True,timeout=5)
sp.run([mount,'-t','tmpfs','-o','size=1m,nodev,nosuid','tmpfs',str(root/'nested')],check=True,timeout=5)
sp.run([mount,'--bind',str(root/'source'),str(root/'bind')],check=True,timeout=5)
assert (root/'bind/sentinel').read_bytes()==b'outside sentinel\n'
(root/'nested/inside').write_text('private tmpfs\n')
mounts=Path('/proc/self/mountinfo').read_text().splitlines()
rows={line.split()[4]:line.split()[:6] for line in mounts}
assert str(root/'nested') in rows and str(root/'bind') in rows
assert rows[str(root/'nested')][0] != rows[str(root/'bind')][0]
print(json.dumps(dict(nested=rows[str(root/'nested')],bind=rows[str(root/'bind')],private_namespace=True)))
