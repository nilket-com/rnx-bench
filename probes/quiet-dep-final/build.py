"""Matched stock binaries for the startup gate (baseline worktree, product checkout); a stock
install of the product from a fixture origin for the transition timings, with Polars built once."""
from common import *
import importlib.util
assert not T.exists() and not O.exists()
T.mkdir(); O.mkdir(parents=True)
(T / 'cargo-home').mkdir()
(T / 'cargo-home/registry').symlink_to(Path.home() / '.cargo/registry', target_is_directory=True)
head = run(['git', 'rev-parse', '--short', 'HEAD']).stdout.decode().strip()
assert head == PRODUCT, head
assert not run(['git', '-c', 'color.ui=false', 'diff', PRODUCT, '--', '.', ':(exclude)README.md', ':(exclude)plans/**']).stdout
save('source.json', {'baseline': BASELINE, 'product': PRODUCT, 'allowed_differences': 'plan/evidence text only'})
run(['git', 'worktree', 'add', '--detach', T / 'before', BASELINE])
for name, source in [('baseline', T / 'before'), ('stock', R)]:
    p = run(['cargo', 'build', '--release', '--locked', '--offline', '--bin', 'rnx', '-j', '8'], cwd=source)
    (O / (name + '-build.log')).write_bytes(p.stdout + p.stderr)
    shutil.copy2(source / 'target/release/rnx', T / name)
save('binaries.json', {k: {'path': str(T / k), 'sha256': sha(T / k), 'size': (T / k).stat().st_size} for k in ['baseline', 'stock']})
# The transition fixture: a stock install whose `repository` is a private origin (0067's pattern).
bare = T / 'origin.git'
run(['git', 'init', '--bare', '-q', bare])
work = T / 'fixture'
run(['git', 'clone', '-q', '--no-hardlinks', R, work])
git(work, 'checkout', '-q', '--detach', PRODUCT)
manifest = work / 'Cargo.toml'
manifest.write_text(manifest.read_text().replace('repository = "https://github.com/nilket-com/rnx"', f'repository = "{bare.as_uri()}"'))
git(work, 'add', 'Cargo.toml')
git(work, 'commit', '-qm', 'fixture: private origin')
fixture_rev = git(work, 'rev-parse', 'HEAD').stdout.decode().strip()
git(work, 'push', '-q', bare, 'HEAD:refs/heads/main')
run(['cargo', 'install', '--git', bare.as_uri(), '--rev', fixture_rev, 'rnx', '--locked', '--root', T / 'install', '--target-dir', T / 'install-target'], timeout=3600)
save('origin.json', {'url': bare.as_uri(), 'fixture_rev': fixture_rev, 'installed': str(T / 'install/bin/rnx'), 'installed_sha256': sha(T / 'install/bin/rnx')})
print('matched binaries and the transition fixture are ready', flush=True)
