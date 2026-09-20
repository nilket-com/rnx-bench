"""Dependency audits: the stock and runner-only graphs carry no Polars; the generated
presenting artifact carries no management symbols; the packaged-manifest test."""
from common import *
checks = []
for name, manifest, flags in [('stock', R / 'Cargo.toml', []), ('runner', R / 'Cargo.toml', ['--no-default-features', '--features', 'count-allocations,project-sources']),
                              ('server', R / 'Cargo.toml', ['--features', 'server-runtime']), ('polars', R / 'adapters/polars/Cargo.toml', []),
                              ('postgres', R / 'adapters/postgres/Cargo.toml', []), ('http-postgres', R / 'servers/http-postgres/Cargo.toml', [])]:
    p = run(['cargo', 'tree', '--locked', '--offline', '--manifest-path', manifest, '--prefix', 'none', *flags])
    text = p.stdout.decode()
    (O / (name + '-tree.txt')).write_text(text)
    # The management crate rides with the default feature; server-runtime adds to it.
    assert ('rnx-project v' in text) == (name in ('stock', 'server')), name
    if name in ['stock', 'runner', 'server']:
        assert 'polars v' not in text and 'tokio-postgres v' not in text, name
    checks.append({'name': name, 'management': 'rnx-project v' in text, 'packages': len(set(text.split('\n')) - {''})})
for exe in sorted((T / 'cache-0-after').glob('entries/*/artifacts/*')):
    symbols = run(['nm', '-C', exe]).stdout
    assert b'rnx_project::' not in symbols, exe
    checks.append({'generated': exe.parent.parent.name[:12], 'management_symbols': False})
p = run(['cargo', 'test', '--locked', '--offline', '--test', 'release_metadata', '--', '--test-threads=1'])
(O / 'final-packaged-manifest.log').write_bytes(p.stdout + p.stderr)
save('feature-checks.json', checks)
print('feature audits and the packaged-manifest check passed', flush=True)
