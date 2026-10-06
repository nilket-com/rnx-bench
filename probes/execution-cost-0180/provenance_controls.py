"""Wrong manifest/role controls stop before binutils; no subject execution."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile

repo = pathlib.Path(sys.argv[1]).resolve()
bindir = pathlib.Path(sys.argv[2]).resolve()
script = pathlib.Path(__file__).with_name('static.py').resolve()
env = {'PATH':'/usr/bin:/bin', 'HOME':'/home/me', 'LANG':'C.UTF-8', 'PYTHONDONTWRITEBYTECODE':'1'}
results = []
with tempfile.TemporaryDirectory(prefix='0180-pin-controls-') as tmp:
	root = pathlib.Path(tmp)
	for name in ('wrong-manifest', 'wrong-primary-role'):
		r = root / name
		(r / 'probes/startup-0179').mkdir(parents=True)
		data = (repo / 'probes/startup-0179/subjects.json').read_bytes()
		(r / 'probes/startup-0179/subjects.json').write_bytes(data + (b'\n' if name == 'wrong-manifest' else b''))
		b = r / 'bin'
		b.mkdir()
		for path in bindir.iterdir():
			os.symlink(path, b / path.name)
		if name == 'wrong-primary-role':
			(b / 'p0-base-primary').unlink()
			os.symlink(bindir / 'p0-cand-primary', b / 'p0-base-primary')
		out = r / 'out'
		argv = [sys.executable, str(script), str(r), str(b), str(out)]
		p = subprocess.run(argv, env=env, capture_output=True, timeout=30)
		wanted = 'manifest hash' if name == 'wrong-manifest' else 'binary hash: p0-base-primary'
		assert p.returncode == 1 and wanted in p.stderr.decode()
		assert json.loads((out / 'ledger.json').read_text()) == []
		assert not (out / 'arithmetic.json').exists()
		results.append({'name':name,'exit':p.returncode,'named_refusal':wanted,'binutils_commands':0,
			'stderr_sha256':hashlib.sha256(p.stderr).hexdigest()})
print(json.dumps({'completed':True,'source_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'controls':results},indent=1))
