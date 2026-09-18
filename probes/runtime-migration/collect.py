#!/usr/bin/env python3
"""Collect source and binary provenance after the documented fixture sequence."""
import ast
import hashlib
import json
import subprocess
from pathlib import Path

B = Path(__file__).resolve().parents[2]
R = B.parent / 'rnx'
O = B / 'results/runtime-migration-0065'
W = B / 'probes/runtime-migration/target/real'

def read(name):
    return json.loads((O / name).read_text())

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

assert len(read('matrix.json')) == 30
assert len(read('publication/matrix.json')) == 90
assert read('checks.json')['complete']
assert all(c['status'] == 0 for c in read('checks.json')['checks'])
assert read('precommit.json')['started_request_retained']
assert read('scratch.json')['explicit_relock_kept_declared_source']
j = read('journey.json')
assert j['migration']['old_entry_unchanged']
assert j['old_kernel']['started_after_migration']
assert j['old_session']['retained_output_read_after_new_journeys']
assert j['new_default_journeys']['cleanup']['all_gone']
setup = json.loads((W / 'setup.json').read_text())
store = Path(setup['store'])
old = store / 'entries' / j['migration']['old'] / 'source/.git'
new = store / 'entries' / j['migration']['new'] / 'source/.git'
for git in (old, new):
    assert git.is_dir() and not git.is_symlink()
    for forbidden in ('objects/info/alternates', 'commondir', 'gitdir'):
        assert not (git / forbidden).exists()
    assert 'worktree' not in (git / 'config').read_text().lower()
objects = [p.relative_to(old) for p in (old / 'objects').glob('*/*') if p.is_file()]
assert objects
for p in objects:
    assert (new / p).is_file()
    a, b = (old / p).stat(), (new / p).stat()
    assert (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino)
    assert sha(old / p) == sha(new / p)
(O / 'index-independence.json').write_text(json.dumps({
    'independent_git_directories': True,
    'no_alternates_or_worktree_links': True,
    'matching_loose_objects_not_hardlinked': len(objects),
}, indent=2) + '\n')
for p in (B / 'probes/runtime-migration').glob('*.py'):
    ast.parse(p.read_text(), filename=str(p))
changed = subprocess.check_output(['git', 'diff', '--name-only', 'a7c3f7d'], cwd=R, text=True).splitlines()
assert all(p.startswith(('tools/project/', 'plans/')) for p in changed), changed
assert not subprocess.check_output(['git', 'diff', 'a7c3f7d', '--', 'tools/project/Cargo.toml', 'tools/project/Cargo.lock', 'tools/project/src/fingerprint/legacy.rs'], cwd=R)
paths = sorted((R / 'tools/project/src').rglob('*.rs'))
binaries = {
    'release': R / 'tools/project/target/release/rnx-project',
    'test_support': R / 'tools/project/target/debug/rnx-project',
    'real_journey_tool': W / 'bin/rnx-project',
    'new_default_tool': W / 'new/bin/rnx-project',
    'old_tool': Path(setup['old_tool']),
    'stock_launcher': W / 'bin/rnx',
}
assert sha(binaries['release']) == sha(binaries['real_journey_tool']) == sha(binaries['new_default_tool'])
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
(O / 'conditions.json').write_text(json.dumps({
    'rnx_head': head,
    'baseline': 'a7c3f7d',
    'old_runtime_snapshot': '7cd3205',
    'source_sha256': {str(p.relative_to(R)): sha(p) for p in paths},
    'binary_sha256': {n: {'path': str(p), 'sha256': sha(p)} for n, p in binaries.items()},
    'scope': 'tool-only; root and dependency inputs unchanged',
    'provenance_hashes': 'SHA-256 here identifies evidence files, not product identities',
}, indent=2) + '\n')
(O / 'implementation.patch').write_bytes(subprocess.check_output(['git', 'diff', '--binary', 'a7c3f7d', '--', 'tools/project'], cwd=R))
print('Collected 30 migration cases, 90 regression cases, real consumers, and source/binary provenance.')
