"""An entry built by the baseline tool (format-3 identity, placeholder wrapper) under the candidate:
its lock still launches it, and when its executable is missing the candidate rebuilds it with the
generator-three name in a private directory, leaving the lock and the key unchanged."""
from common import *
import shutil
cache = T / 'compat-cache'
env = env_for(cache, T / 'cargo-home')
d = project('compat', [])  # runtime only: a cheap Git-source assembly
run([tool('baseline'), 'lock', '--manifest', d / 'rnx.toml'], cwd=d, env=env, timeout=900)
run([tool('baseline'), 'build', '--manifest', d / 'rnx.toml'], cwd=d, env=env, timeout=1800)
before = (d / 'rnx.lock').read_bytes()
i = identity_of(d)
assert (i['format'], i['generator']) == (3, 3) and 'build' not in i['context'] and package_name(i['manifest']) == 'rnx-project-app', i['context']
out = run([tool('candidate'), 'run', '--manifest', d / 'rnx.toml'], cwd=d, env=env).stdout.decode()
assert out.strip().endswith('42'), out
receipt = json.loads((d / '.rnx/receipt.json').read_text())
artifacts = [p for p in cache.glob('entries/*/artifacts/*') if p.stat().st_ino == receipt['stamp']['inode']]
assert len(artifacts) == 1
artifact = artifacts[0]
entry = artifact.parent.parent
# Lose the executable and the private target: the candidate must rebuild the retained recipe as recorded.
for name in ['artifacts', 'target', 'ready.json']:
    p = entry / name
    if p.is_dir():
        shutil.rmtree(p)
    elif p.exists():
        p.unlink()
p = run([tool('candidate'), 'run', '--manifest', d / 'rnx.toml'], cwd=d, env=env, check=False)
launch_refused = p.returncode != 0
rebuild = run([tool('candidate'), 'build', '--manifest', d / 'rnx.toml'], cwd=d, env=env, timeout=1800)
assert (d / 'rnx.lock').read_bytes() == before, 'the lock must not change on a rebuild'
rebuilt = sorted(entry.glob('artifacts/*'))
assert rebuilt and (entry / 'target/release/rnx-project-app').exists(), 'placeholder name in the entry target'
assert not (cache / 'build').exists(), 'no shared directory for a retained format-three identity'
out = run([tool('candidate'), 'run', '--manifest', d / 'rnx.toml'], cwd=d, env=env).stdout.decode()
assert out.strip().endswith('42'), out
save('compatibility.json', {'identity_format': [i['format'], i['generator']], 'wrapper': package_name(i['manifest']), 'entry': entry.name,
                            'launch_refused_when_missing': launch_refused, 'rebuild_seconds': None, 'rebuilt_with_placeholder': True, 'lock_unchanged': True})
print('compatibility: a format-three lock launches under the candidate and rebuilds its missing entry with the generator-three name, privately, lock unchanged', flush=True)
