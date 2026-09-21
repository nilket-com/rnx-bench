"""A bare origin holding the product and the baseline; stock installs of both from it (`cargo
install --git`), runner-only session builds of both for the cross-version directions."""
from common import *
import shutil
assert not T.exists() and not O.exists()
T.mkdir(); O.mkdir(parents=True)
assert not run(['git', '-c', 'color.ui=false', 'diff', PRODUCT, '--', '.', ':(exclude)plans/**'], cwd=R).stdout
bare = T / 'origin.git'
run(['git', 'init', '--bare', '-q', bare])
url = bare.as_uri()
# A stock install takes its runtime coordinate from the crate's `repository`: as in 0067's
# journey, a fixture commit on each revision points it at this origin (manifest change only).
revs = {}
for label, rev in [('product', PRODUCT), ('baseline', BASELINE)]:
    work = T / f'fixture-{label}'
    run(['git', 'clone', '-q', '--no-hardlinks', R, work])
    git(work, 'checkout', '-q', '--detach', rev)
    manifest = work / 'Cargo.toml'
    text = manifest.read_text()
    assert 'repository = "https://github.com/nilket-com/rnx"' in text
    manifest.write_text(text.replace('repository = "https://github.com/nilket-com/rnx"', f'repository = "{url}"'))
    git(work, 'add', 'Cargo.toml')
    git(work, 'commit', '-qm', f'fixture: private origin ({label} {rev})')
    full = git(work, 'rev-parse', 'HEAD').stdout.decode().strip()
    git(work, 'push', '-q', bare, f'HEAD:refs/heads/{label}')
    revs[label] = {'source': run(['git', 'rev-parse', rev], cwd=R).stdout.decode().strip(), 'fixture': full}
(T / 'cargo-home').mkdir()
(T / 'cargo-home/registry').symlink_to(Path.home() / '.cargo/registry', target_is_directory=True)
env = dict(ENV, CARGO_HOME=str(T / 'cargo-home'))
installed = {}
for label in ['product', 'baseline']:
    root = T / f'install-{label}'
    run(['cargo', 'install', '--git', url, '--rev', revs[label]['fixture'], 'rnx', '--locked', '--root', root, '--target-dir', T / f'install-target-{label}'], env=env, timeout=3600)
    installed[label] = str(root / 'bin/rnx')
    # A runner-only session (no management): it consults RNX_PROJECT_TOOL.
    work = T / f'src-{label}'
    work.mkdir()
    run(['git', 'clone', '-q', '--no-hardlinks', bare, work])
    git(work, 'checkout', '-q', revs[label]['fixture'])
    run(['cargo', 'build', '--release', '--locked', '--offline', '--no-default-features', '--features', 'count-allocations,project-sources', '--bin', 'rnx',
         '--target-dir', T / f'runner-target-{label}'], cwd=work, env=env, timeout=3600)
    installed[f'{label}-runner'] = str(T / f'runner-target-{label}/release/rnx')
    if label == 'product':
        # A test-support stock build: only for the pause at the exec boundary.
        run(['cargo', 'build', '--release', '--locked', '--offline', '--features', 'test-support', '--bin', 'rnx', '--target-dir', T / 'support-target'], cwd=work, env=env, timeout=3600)
        installed['product-support'] = str(T / 'support-target/release/rnx')
save('prepare.json', {'product': PRODUCT, 'baseline': BASELINE, 'revs': revs, 'origin': url, 'binaries': {k: {'path': v, 'sha256': sha(Path(v).read_bytes())} for k, v in installed.items()}})
print('origin, two stock installs and two runner-only sessions ready', flush=True)
