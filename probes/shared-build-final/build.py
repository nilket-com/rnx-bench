"""Matched stock binaries (the baseline worktree at BASELINE and the checkout at PRODUCT), a bare
Git origin of the baseline tree for Git-source projects, and a private Cargo home sharing the
registry cache. The origin is the baseline tree: both binaries build the same runtime and
adapters from it, and only the tool differs."""
from common import *
assert not T.exists() and not O.exists()
T.mkdir(); O.mkdir(parents=True)
# The private Cargo home is in every command's environment: it exists, with the registry cache, first.
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
# The origin: the baseline tree, bare, by file URL; a private Cargo home with the registry cache.
bare = T / 'origin.git'
run(['git', 'init', '--bare', '-q', bare])
git(T / 'before', 'push', '-q', bare, 'HEAD:refs/heads/origin-main')
rev = git(T / 'before', 'rev-parse', 'HEAD').stdout.decode().strip()
save('origin.json', {'url': bare.as_uri(), 'rev': rev})
print('matched binaries, the origin and a private Cargo home are ready', flush=True)
