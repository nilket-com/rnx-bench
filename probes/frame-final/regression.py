"""Formatting, the three root configurations, the tool, the adapters, notices and strict
clippy on the product checkout; root clippy against a real baseline invocation."""
from common import *
rows = []
def check(name, args, ok=True, cwd=R):
    p = run(args, cwd=cwd, ok=False)
    (O / (name + '.log')).write_bytes(p.stdout + p.stderr)
    rows.append({'name': name, 'args': list(map(str, args)), 'status': p.returncode})
    save('regression.json', rows)
    print(name, p.returncode, flush=True)
    if ok:
        assert p.returncode == 0, name
    return p
check('root-fmt', ['cargo', 'fmt', '--check'])
check('tool-fmt', ['cargo', 'fmt', '--manifest-path', 'tools/project/Cargo.toml', '--check'])
check('polars-fmt', ['cargo', 'fmt', '--manifest-path', 'adapters/polars/Cargo.toml', '--check'])
for name, flags in [('default', []), ('support', ['--features', 'test-support']),
                    ('runner', ['--no-default-features', '--features', 'count-allocations,project-sources'])]:
    check('root-' + name, ['cargo', 'test', '--locked', '--offline', '-j', '6', *flags, '--', '--test-threads=1'])
for name, flags in [('default', []), ('support', ['--features', 'test-support'])]:
    check('tool-' + name, ['cargo', 'test', '--locked', '--offline', '--manifest-path', 'tools/project/Cargo.toml', '-j', '4', *flags, '--', '--test-threads=1'])
    check('tool-clippy-' + name, ['cargo', 'clippy', '--locked', '--offline', '--manifest-path', 'tools/project/Cargo.toml', '--all-targets', *flags, '--', '-D', 'warnings'])
    check('polars-' + name, ['cargo', 'test', '--locked', '--offline', '--manifest-path', 'adapters/polars/Cargo.toml', '-j', '4', *flags, '--', '--test-threads=1'])
    check('polars-clippy-' + name, ['cargo', 'clippy', '--locked', '--offline', '--manifest-path', 'adapters/polars/Cargo.toml', '--all-targets', *flags, '--', '-D', 'warnings'])
check('root-notices', ['bash', 'scripts/third-party-notices.sh', '--check'])
check('tool-notices', ['python3', 'tools/project/scripts/notices.py', '--check'])
check('polars-notices', ['python3', 'adapters/polars/scripts/third-party-notices.py', '--check'])
check('selfcheck', [T / 'stock', 'selfcheck'])
# Root strict clippy has findings that predate this record: compared, not hidden.
check('root-clippy', ['cargo', 'clippy', '--locked', '--offline', '--all-targets', '--', '-D', 'warnings'], ok=False)
check('baseline-clippy', ['cargo', 'clippy', '--locked', '--offline', '--all-targets', '--', '-D', 'warnings'], ok=False, cwd=T / 'before')
def diagnostics(text):
    out = []
    lines = text.splitlines()
    for i, l in enumerate(lines):
        if l.startswith(('error', 'warning')) and not l.startswith(('error: could not compile', 'warning: build failed', 'warning: `rnx`')):
            where = next((x.strip() for x in lines[i + 1:i + 3] if x.strip().startswith('-->')), '')
            out.append(l + ' ' + where.split(':')[0])
    return sorted(out)
base = diagnostics((O / 'baseline-clippy.log').read_text(errors='replace'))
cur = diagnostics((O / 'root-clippy.log').read_text(errors='replace'))
save('clippy-comparison.json', {'baseline': base, 'current': cur, 'added': sorted(set(cur) - set(base)), 'removed': sorted(set(base) - set(cur))})
assert set(cur) <= set(base), sorted(set(cur) - set(base))
for path in ['adapters/postgres', 'servers/http-postgres']:
    name = path.replace('/', '-')
    check(name + '-tests', ['cargo', 'test', '--locked', '--offline', '--manifest-path', path + '/Cargo.toml', '-j', '4', '--', '--test-threads=1'])
    check(name + '-notices', ['python3', path + '/scripts/third-party-notices.py', '--check'])
print('regression complete', flush=True)
