#!/usr/bin/env python3
"""Record 0056 gate 2; Linux subprocess controls and public-surface checks."""
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
BENCH = HERE.parents[1]
ROOT = BENCH.parent / 'rnx'
OUT = BENCH / 'results/server-host-0056'
if sys.platform != 'linux':
    raise SystemExit('gate 2 execution evidence requires Linux')
OUT.mkdir(parents=True, exist_ok=True)

def run(args, filename):
    process = subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        text, _ = process.communicate(timeout=300)
    except BaseException:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        raise
    (OUT / filename).write_text(text)
    if process.returncode:
        raise RuntimeError(f'{filename}: exit {process.returncode}; see captured output')
    return text

host = run(['cargo', 'test', '--locked', '--features', 'server-runtime,test-support',
            '--lib', 'server::host_tests::subprocess_host_boundary', '--', '--exact',
            '--nocapture'], 'host.txt')
assert host.count('HOST ') == 3, host
assert 'config reads=0 then control=1' in host
assert 'HOST released native poll and joined worker' in host
run(['cargo', 'test', '--locked', '--features', 'server-runtime', '--doc'], 'doc-tests.txt')
run(['cargo', 'doc', '--locked', '--features', 'server-runtime', '--no-deps'], 'doc-build.txt')
public = ROOT / 'target/doc/rnx/server'
items = sorted(p.name for p in public.glob('struct.*.html'))
assert items == ['struct.Failure.html', 'struct.Invocation.html', 'struct.Program.html'], items
for kind in ['fn', 'enum', 'trait', 'type', 'constant', 'static']:
    assert not list(public.glob(kind + '.*.html')), kind
conditions = {
    'root_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'server_source_sha256': hashlib.sha256((ROOT / 'src/server.rs').read_bytes()).hexdigest(),
    'rustc': subprocess.check_output(['rustc', '--version'], text=True).strip(),
    'public_types': items,
    'platform': sys.platform,
    'scope': 'tests and docs only; gate 2, not server extraction',
}
(OUT / 'conditions.json').write_text(json.dumps(conditions, indent=2) + '\n')
print('PASS host subprocesses, five compile-fail docs, exactly three public types')
