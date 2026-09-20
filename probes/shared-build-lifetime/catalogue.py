"""The catalogue writes the declaration for a Git runtime: `add polars postgres` produces
`shared_build = true` on both, the project locks shared, an existing undeclared declaration is
left alone, and a path runtime gets no declaration."""
from common import *
prep = json.loads((O / 'prepare.json').read_text())
url, rev1 = prep['origin_url'], prep['origin_rev']
d = T / 'projects' / 'catalogue-git'
d.mkdir(parents=True)
(d / 'main.rn').write_text('pub fn main(_) { 42 }\n')
(d / 'rnx.toml').write_text(f'format = 2\n[application]\nentry = "main.rn"\n[runtime]\ngit = "{url}"\nrev = "{rev1}"\n')
run([RNX, 'project', 'add', 'polars', 'postgres', '--manifest', d / 'rnx.toml'], cwd=d, env=env_for(), timeout=120)
text = (d / 'rnx.toml').read_text()
assert text.count('shared_build = true') == 2 and 'presentation = true' in text.split('[native.polars]')[1].split('[native.postgres]')[0]
run([RNX, 'project', 'lock', '--manifest', d / 'rnx.toml'], cwd=d, env=env_for(), timeout=900)
i = identity_of(d)
assert i['context']['build']['kind'] == 'shared', i['context']['build']
# An existing declaration without the field is left alone by a later add.
e = T / 'projects' / 'catalogue-existing'
e.mkdir(parents=True)
(e / 'main.rn').write_text('pub fn main(_) { 42 }\n')
(e / 'rnx.toml').write_text(f'format = 2\n[application]\nentry = "main.rn"\n[runtime]\ngit = "{url}"\nrev = "{rev1}"\n\n[native.polars]\ngit = "{url}"\nrev = "{rev1}"\npackage = "rnx-polars"\nbuilder = "build"\nhook = "plain"\npresentation = true\n')
before = (e / 'rnx.toml').read_text()
out = run([RNX, 'project', 'add', 'polars', '--manifest', e / 'rnx.toml'], cwd=e, env=env_for(), timeout=120)
assert (e / 'rnx.toml').read_text() == before, 'an existing declaration is not rewritten'
run([RNX, 'project', 'lock', '--manifest', e / 'rnx.toml'], cwd=e, env=env_for(), timeout=900)
assert identity_of(e)['context']['build'] == {'kind': 'private'}
# A path runtime: the field is not written and the identity has no build kind.
p = T / 'projects' / 'catalogue-path'
p.mkdir(parents=True)
(p / 'main.rn').write_text('pub fn main(_) { 42 }\n')
(p / 'rnx.toml').write_text(f'format = 1\n[application]\nentry = "main.rn"\n[runtime]\npath = "{T / "product"}"\n')
run([RNX, 'project', 'add', 'polars', '--manifest', p / 'rnx.toml'], cwd=p, env=env_for(), timeout=120)
assert 'shared_build' not in (p / 'rnx.toml').read_text()
save('catalogue.json', {'git_manifest': text, 'git_build': i['context']['build'], 'existing_unchanged': True, 'path_manifest': (p / 'rnx.toml').read_text()})
print('catalogue: add writes shared_build = true for Git declarations of both adapters; existing and path declarations are left alone', flush=True)
