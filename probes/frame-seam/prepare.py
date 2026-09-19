"""Archive the baseline, apply the candidate patch, build both trees' tools and the candidate runtime."""
from common import *
import io, shutil, tarfile
assert not T.exists(), f'{T} must be absent'
T.mkdir()
archive = run(['git', 'archive', BASELINE_REV], cwd=R).stdout
for label in ('baseline', 'candidate'):
    root = T / label
    root.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(root, filter='data')
# Each tree is its own repository first: `git apply` inside an enclosing
# repository resolves paths against that repository's root and patches nothing.
for label in ('baseline', 'candidate'):
    run(['git', 'init', '-q', T / label])
run(['git', '-C', T / 'candidate', 'apply', H / 'candidate.patch'])
assert (T / 'candidate/src/present.rs').exists(), 'candidate patch did not apply'
# Cargo needs the tracked snapshot to be a Git working tree for native inventory.
for label in ('baseline', 'candidate'):
    root = T / label
    run(['git', '-C', root, 'add', '-A'])
    run(['git', '-C', root, '-c', 'user.name=probe', '-c', 'user.email=probe@localhost', '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', label])
cand = T / 'candidate'
run(['cargo', 'build', '--locked', '--offline', '--release', '--manifest-path', cand / 'Cargo.toml'], timeout=1800)
run(['cargo', 'build', '--locked', '--offline', '--release', '--manifest-path', cand / 'tools/project/Cargo.toml', '--bin', 'rnx-project'], timeout=1800)
run(['cargo', 'build', '--locked', '--offline', '--features', 'test-support', '--manifest-path', cand / 'tools/project/Cargo.toml', '--bin', 'rnx-project-assembly-probe'], timeout=1800)
run(['cargo', 'build', '--locked', '--offline', '--release', '--manifest-path', T / 'baseline/tools/project/Cargo.toml', '--bin', 'rnx-project', '--target-dir', T / 'baseline-tool'], timeout=1800)
save('prepare.json', {
    'baseline_rev': run(['git', 'rev-parse', BASELINE_REV], cwd=R).stdout.decode().strip(),
    'candidate_patch_sha256': sha((H / 'candidate.patch').read_bytes()),
    'candidate_rnx_sha256': sha((cand / 'target/release/rnx').read_bytes()),
    'candidate_tool_sha256': sha(tool('candidate').read_bytes()),
    'baseline_tool_sha256': sha(tool('baseline').read_bytes()),
})
print('prepared baseline and candidate trees and tools', flush=True)
