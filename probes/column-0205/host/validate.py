"""Build the report-only host comparator, then validate all paths before measurement."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import traceback

ROOT = Path('<RNX_ROOT>')
HERE = Path(__file__).resolve().parent
OUT = HERE / 'validation-v1'
OUT.mkdir(exist_ok=False)
result = {'status': 'FAIL', 'checks': []}
started = time.monotonic()
env = dict(os.environ, CARGO_BUILD_JOBS='4')

def run(name, command):
	with (OUT / (name + '.stdout')).open('x') as stdout, (OUT / (name + '.stderr')).open('x') as stderr:
		p = subprocess.run(command, cwd=HERE, env=env, stdout=stdout, stderr=stderr, timeout=10800)
	result['checks'].append({'name': name, 'exit': p.returncode})
	assert p.returncode == 0, name

try:
	result['source_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
	assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()
	(HERE / 'Cargo.lock').write_bytes((ROOT / 'Cargo.lock').read_bytes())
	# Seed from the product lock; metadata removes irrelevant packages and adds only this probe.
	run('resolve', ['cargo', '+1.98.1', 'metadata', '--offline', '--format-version', '1'])
	import tomllib
	product = tomllib.loads((ROOT / 'Cargo.lock').read_text())['package']
	probe = tomllib.loads((HERE / 'Cargo.lock').read_text())['package']
	known = {(p['name'], p['version'], p.get('source'), p.get('checksum')) for p in product}
	assert all((p['name'], p['version'], p.get('source'), p.get('checksum')) in known for p in probe if p['name'] != 'column-0205-headline'), 'dependency resolution differs from product'
	result['lock_sha256'] = hashlib.sha256((HERE / 'Cargo.lock').read_bytes()).hexdigest()
	run('format', ['cargo', '+1.98.1', 'fmt', '--', '--check'])
	run('clippy', ['cargo', '+1.98.1', 'clippy', '--locked', '--release', '--no-deps', '--', '-D', 'warnings'])
	run('build', ['cargo', '+1.98.1', 'build', '--locked', '--release'])
	binary = HERE / 'target/release/column-0205-headline'
	result['binary'] = str(binary)
	result['binary_sha256'] = hashlib.sha256(binary.read_bytes()).hexdigest()
	for mode in ('auto', 'portable', 'reference'):
		run('control-' + mode, [str(binary), mode, '4096'])
		data = json.loads((OUT / ('control-' + mode + '.stdout')).read_text())
		assert data['status'] == 'PASS' and data['rows'] == 4096 and len(data['samples']) == 2
	assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == result['source_commit']
	assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()
	result['status'] = 'PASS'
except BaseException as error:
	result['error'] = repr(error)
	(OUT / 'TRACEBACK.txt').write_text(traceback.format_exc())
finally:
	result['seconds'] = time.monotonic() - started
	(OUT / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
	summary = '0205 headline host comparator validation EXIT ' + result['status']
	notice = OUT / 'NOTICE.txt'
	notice.write_text(summary + '. Receipt: ' + str(OUT / 'RESULT.json') + '\n')
	subprocess.run(['chatctl', 'send', '--as', 'sluice', '--to', 'codex', '--conversation', 'rune-native', '--summary', summary, '--body-file', str(notice)], check=True)
raise SystemExit(0 if result['status'] == 'PASS' else 1)
