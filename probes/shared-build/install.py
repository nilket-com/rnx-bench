"""The launcher installed from a Git source as a fresh user does it (`cargo install --git`), once
plain and once with the canonical shared build directory retained. Hashes are reported; byte
equality between the two is not expected and not asserted."""
from common import *
rev = run(['git', 'rev-parse', PRODUCT]).stdout.decode().strip()
rows = {}
for name, config in [('plain', []), ('shared', ['--config', f'build.build-dir="{SHARED}"'])]:
    root = T / f'install-{name}'
    p = run(['cargo', 'install', '--git', f'file://{R}', '--rev', rev, 'rnx', '--root', root, '--locked', *config], timeout=3600)
    err = p.stderr.decode(errors='replace')
    entries = compiling(err)
    (O / f'install-{name}.log').write_text(err)
    rows[name] = {'seconds': p.seconds, 'compiling_entries': len(entries), 'exe_sha256': sha(root / 'bin/rnx'),
                  'retained_fingerprints': len(list((SHARED / 'release/.fingerprint').iterdir())) if name == 'shared' else 0,
                  'build_dir_bytes': bytes_under(SHARED) if name == 'shared' else 0}
    print(f"install {name}: {p.seconds} s, {len(entries)} Compiling entries", flush=True)
snapshot('after-install')
shutil.rmtree(SHARED)
save('install.json', rows)
