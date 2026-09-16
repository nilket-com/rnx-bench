#!/usr/bin/env python3
"""Record the source-only probe's build inputs and resolved license inventory."""
import hashlib
import importlib.metadata
import json
import pathlib
import platform
import subprocess
import tomllib

HERE = pathlib.Path(__file__).resolve().parent
BENCH = HERE.parents[1]
ROOT = BENCH.parent / 'rnx'
OUT = BENCH / 'results/package-boundary'

def command(*args):
    return subprocess.check_output(args, text=True).strip()

def packages(lock):
    return {(p['name'], p['version']) for p in tomllib.loads(lock.read_text())['package']}

conditions = {
    'platform': platform.platform(),
    'rustc': command('rustc', '-Vv'),
    'cargo': command('cargo', '-V'),
    'rnx_head': command('git', '-C', str(ROOT), 'rev-parse', 'HEAD'),
    'bench_base': command('git', '-C', str(BENCH), 'rev-parse', 'HEAD'),
    'python': platform.python_version(),
    'python_packages': {name: importlib.metadata.version(name) for name in
                        ('jupyter_client', 'pyzmq', 'jupyter_core')},
    'files': {},
    'dependency_differences': {},
}
for name, manifest, baseline in (
    ('source', HERE / 'Cargo.toml', ROOT / 'Cargo.lock'),
    ('native', HERE / 'target/native/generated-a/Cargo.toml', ROOT / 'adapters/postgres/Cargo.lock'),
):
    graph = json.loads(command('cargo', 'metadata', '--locked', '--offline',
                              '--format-version', '1', '--manifest-path', str(manifest)))
    inventory = [{'name': p['name'], 'version': p['version'], 'source': p['source'],
                  'license': p['license'], 'license_file': p['license_file']}
                 for p in graph['packages']]
    (OUT / (name + '-graph.json')).write_text(json.dumps(inventory, indent=2) + '\n')
    conditions['dependency_differences'][name] = sorted(packages(manifest.with_name('Cargo.lock')) - packages(baseline))
for relative in ('Cargo.toml', 'Cargo.lock', 'src/main.rs', 'source.py', 'native.py', 'conditions.py'):
    conditions['files'][relative] = hashlib.sha256((HERE / relative).read_bytes()).hexdigest()
(OUT / 'conditions.json').write_text(json.dumps(conditions, indent=2) + '\n')
print(json.dumps(conditions['dependency_differences'], indent=2))
