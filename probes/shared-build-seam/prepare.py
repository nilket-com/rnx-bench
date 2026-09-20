"""Baseline tree at BASELINE_REV and the candidate (baseline + candidate.patch), each its own repository;
both tools built; a bare Git origin of the baseline for Git-source projects; a private Cargo home
sharing the registry cache."""
from common import *
import io, shutil, tarfile
assert not T.exists() and not O.exists()
T.mkdir(); O.mkdir(parents=True)
archive = run(['git', 'archive', BASELINE_REV], cwd=R).stdout
for label in ['baseline', 'candidate']:
    (T / label).mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(T / label, filter='data')
    git(T / label, 'init', '-q')
run(['git', '-C', T / 'candidate', 'apply', H / 'candidate.patch'])
for label in ['baseline', 'candidate']:
    git(T / label, 'add', '-A')
    git(T / label, 'commit', '-q', '-m', label)
cand = T / 'candidate'
run(['cargo', 'build', '--locked', '--offline', '--release', '--manifest-path', cand / 'tools/project/Cargo.toml', '--bin', 'rnx-project'], timeout=1800)
run(['cargo', 'build', '--locked', '--offline', '--features', 'test-support', '--manifest-path', cand / 'tools/project/Cargo.toml', '--bin', 'rnx-project-assembly-probe'], timeout=1800)
run(['cargo', 'build', '--locked', '--offline', '--release', '--manifest-path', T / 'baseline/tools/project/Cargo.toml', '--bin', 'rnx-project', '--target-dir', T / 'baseline-tool'], timeout=1800)
# The Git origin: the baseline tree (runtime and adapters), bare, addressed by file URL.
bare = T / 'origin.git'
run(['git', 'init', '--bare', '-q', bare])
git(T / 'baseline', 'push', '-q', bare, 'HEAD:refs/heads/main')
rev = git(T / 'baseline', 'rev-parse', 'HEAD').stdout.decode().strip()
home = T / 'cargo-home'
home.mkdir()
(home / 'registry').symlink_to(Path.home() / '.cargo/registry', target_is_directory=True)
save('prepare.json', {'baseline_rev': run(['git', 'rev-parse', BASELINE_REV], cwd=R).stdout.decode().strip(), 'candidate_patch_sha256': sha((H / 'candidate.patch').read_bytes()),
                      'origin_url': bare.as_uri(), 'origin_rev': rev, 'cargo_home': str(home),
                      'tools': {k: sha(tool(k).read_bytes()) for k in ['candidate', 'candidate-probe', 'baseline']}})
print('baseline and candidate trees, both tools, the fixture origin and a private Cargo home are ready', flush=True)
