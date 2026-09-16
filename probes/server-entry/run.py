#!/usr/bin/env python3
"""Run record 0056 gate 1 through the public, separately built crate."""
import hashlib
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
BENCH = HERE.parents[1]
ROOT = BENCH.parent / 'rnx'
RESULTS = BENCH / 'results' / 'server-entry-0056'
RESULTS.mkdir(parents=True, exist_ok=True)

def command(args, cwd=HERE):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True,
                          check=True, timeout=300)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

command(['cargo', 'build', '--locked', '--quiet'])
binary = HERE / 'target/debug/rnx-server-entry-fixture'
for n in (1, 2):
    result = command([str(binary)])
    assert not result.stderr, result.stderr
    assert len(result.stdout.splitlines()) == 8, result.stdout
    assert all(line.startswith('PASS ') for line in result.stdout.splitlines())
    (RESULTS / f'run-{n}.txt').write_text(result.stdout)
conditions = {
    'rnx_head': command(['git', 'rev-parse', 'HEAD'], ROOT).stdout.strip(),
    'rnx_status': command(['git', 'status', '--porcelain'], ROOT).stdout.splitlines(),
    'rustc': command(['rustc', '--version']).stdout.strip(),
    'binary_sha256': sha(binary),
    'lock_sha256': sha(HERE / 'Cargo.lock'),
    'rnx_files_sha256': {name: sha(ROOT / name) for name in
        ['src/server.rs', 'src/extensions.rs', 'src/process.rs', 'src/lib.rs', 'Cargo.toml', 'Cargo.lock']},
    'fixture_sha256': sha(HERE / 'src/main.rs'),
    'profile': 'debug; dependencies opt-level=2; not a latency benchmark',
}
(RESULTS / 'conditions.json').write_text(json.dumps(conditions, indent=2) + '\n')
print('PASS two public-API fixture runs; eight assertions groups each; empty stderr')
