#!/usr/bin/env python3
"""Build the public-API fixture; prove capability dispatch skips its builder."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
ROOT = BENCH.parent / 'rnx'
OUT = BENCH / 'results/package-inputs-0057'
OUT.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, CARGO_TARGET_DIR=str(ROOT / 'target'))
subprocess.run(['cargo', 'build', '--locked', '--offline', '--manifest-path', str(HERE / 'fixture/Cargo.toml')], env=env, check=True)
binary = ROOT / 'target/debug/rnx-package-input-fixture'
with tempfile.TemporaryDirectory(prefix='rnx0057-capability-') as root:
    p = Path(root)
    env = {k: v for k, v in os.environ.items() if not k.startswith('RNX_')}
    env.update(TERM='xterm', NO_COLOR='1', RNX_GATE2_BUILDER=str(p/'builder'),
               RNX_TEST_CONFIG_READS=str(p/'reads'), RNX_CONFIG=str(p/'invalid'))
    (p/'invalid').write_text('not valid Rune')
    cap = subprocess.run([binary, 'project-source-version'], env=env, capture_output=True, text=True, timeout=10)
    assert (cap.returncode, cap.stdout, cap.stderr) == (0, '{"format":1}\n', ''), cap
    assert not (p/'builder').exists()
    assert (p/'reads').read_text() == '0'
    serving = subprocess.run([binary, 'eval', '42'], env=env, capture_output=True, text=True, timeout=10)
    assert (serving.returncode, serving.stdout, serving.stderr) == (0, '42\n', ''), serving
    assert (p/'builder').read_text() == 'builder ran'
    # Supply the accepted pre-feature binary explicitly on later reruns.
    old = Path(os.environ.get('RNX_GATE2_OLD_BINARY', ROOT/'target/release/rnx'))
    refused = subprocess.run([old, 'project-source-version'], env=env, capture_output=True, text=True, timeout=10)
    assert refused.returncode != 0 and not refused.stdout, refused
    result = {
        'fixture_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
        'capability': cap.stdout, 'builder_calls_before_serving': 0, 'config_reads': 0,
        'positive_control': serving.stdout, 'builder_positive_control': True,
        'unsupported_binary_sha256': hashlib.sha256(old.read_bytes()).hexdigest(),
        'unsupported_status': refused.returncode, 'unsupported_stderr': refused.stderr,
    }
    (OUT/'capability.json').write_text(json.dumps(result, indent=2)+'\n')
print('capability fixture passed')
