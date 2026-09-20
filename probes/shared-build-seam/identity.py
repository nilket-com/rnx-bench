"""Locks with the candidate tool on Git-source projects: the wrapper name is the content digest,
equal wrappers share a name and a key across projects, the build kind follows the one eligibility
rule, and a path native with the declaration stays private."""
from common import *
import shutil
cache = T / 'identity-cache'
env = env_for(cache, T / 'cargo-home')
polars = 'presentation = true\n'
cases = {
    'polars': [('polars', 'rnx-polars', 'plain', polars)],
    'polars-again': [('polars', 'rnx-polars', 'plain', polars)],
    'polars-shared': [('polars', 'rnx-polars', 'plain', polars + 'shared_build = true\n')],
    'polars-plain-shared': [('polars', 'rnx-polars', 'plain', 'shared_build = true\n')],
    'both-shared': [('polars', 'rnx-polars', 'plain', polars + 'shared_build = true\n'), ('postgres', 'rnx-postgres', 'lifecycle', 'shared_build = true\n')],
    'both-one-declared': [('polars', 'rnx-polars', 'plain', polars + 'shared_build = true\n'), ('postgres', 'rnx-postgres', 'lifecycle', '')],
    'none': [],
}
rows = {}
for name, natives in cases.items():
    d = project(name, natives)
    run([tool('candidate'), 'lock', '--manifest', d / 'rnx.toml'], cwd=d, env=env, timeout=900)
    i = identity_of(d)
    rows[name] = {'format': i['format'], 'generator': i['generator'], 'build': i['context']['build'], 'wrapper': package_name(i['manifest']),
                  'key': sha(json.loads((d / 'rnx.lock').read_text())['assembly']['identity'].encode())[:16], 'main': i['main']}
# A path native carrying the declaration: accepted, recorded, private.
adapter = T / 'identity-adapter'
shutil.copytree(T / 'baseline/adapters/polars', adapter)
(adapter / 'Cargo.toml').write_text((adapter / 'Cargo.toml').read_text().replace('path = "../.."', f'path = "{T / "baseline"}"'))
git(adapter, 'init', '-q'); git(adapter, 'add', '-A'); git(adapter, 'commit', '-q', '-m', 'adapter')
d = project('path-native-declared', [], extra=f'\n[native.polars]\npath = "{adapter}"\npackage = "rnx-polars"\nbuilder = "build"\nhook = "plain"\npresentation = true\nshared_build = true\n')
run([tool('candidate'), 'lock', '--manifest', d / 'rnx.toml'], cwd=d, env=env, timeout=900)
i = identity_of(d)
rows['path-native-declared'] = {'format': i['format'], 'generator': i['generator'], 'build': i['context']['build'], 'wrapper': package_name(i['manifest'])}
assert 'shared_build = true' in (d / 'rnx.toml').read_text() and json.loads((d / 'rnx.lock').read_text())['declarations']['native']['polars']['shared_build'] is True
for name, r in rows.items():
    assert (r['format'], r['generator']) == (4, 4), name
    assert r['wrapper'].startswith('rnx-app-') and len(r['wrapper']) == 72, name
assert rows['polars']['wrapper'] == rows['polars-again']['wrapper'] and rows['polars']['key'] == rows['polars-again']['key']
# The declaration changes the build kind and the key, not the wrapper; the presentation call changes the wrapper.
assert rows['polars']['wrapper'] == rows['polars-shared']['wrapper'] and rows['polars']['key'] != rows['polars-shared']['key']
assert rows['polars-shared']['wrapper'] != rows['polars-plain-shared']['wrapper']
assert rows['polars']['build'] == {'kind': 'private'}
assert rows['polars-shared']['build']['kind'] == 'shared' and len(rows['polars-shared']['build']['key']) == 64
assert rows['polars-shared']['build'] == rows['polars-plain-shared']['build'] == rows['both-shared']['build'] == rows['none']['build'], 'one directory per context'
assert rows['both-one-declared']['build'] == {'kind': 'private'}
assert rows['path-native-declared']['build'] == {'kind': 'private'}
save('identity.json', rows)
print(f"identity: digest wrapper names, equal content equal ({rows['polars']['wrapper'][:24]}…), shared key {rows['polars-shared']['build']['key'][:12]}… for every eligible assembly, private otherwise", flush=True)
