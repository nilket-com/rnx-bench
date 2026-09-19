"""Assembly identities: unchanged when `presentation` is omitted, new when enabled; wrapper bytes prove why."""
from common import *
import re
runtime = T / 'candidate'
work = T / 'identity'
work.mkdir(exist_ok=True)
cache = work / 'cache'


def project(name, extra):
    d = work / name
    d.mkdir(exist_ok=True)
    (d / 'main.rn').write_text('pub fn main(_) { println!("{:?}", polars::lit(1)?); }\n')
    (d / 'rnx.toml').write_text(
        f'format = 1\n[application]\nentry = "main.rn"\n[runtime]\npath = "{runtime}"\n'
        f'[native.polars]\npath = "{runtime}/adapters/polars"\npackage = "rnx-polars"\nbuilder = "build"\nhook = "plain"\n{extra}')
    return d


def lock(kind, d):
    run([tool(kind), 'lock', '--manifest', d / 'rnx.toml', '--offline'], env=dict(ENV, RNX_PROJECT_CACHE=str(cache)), timeout=600)
    doc = json.loads((d / 'rnx.lock').read_text())
    identity_text = doc['assembly']['identity']
    identity = json.loads(identity_text)
    # The assembly key is BLAKE3 of the canonical identity bytes, as build computes it.
    src = d / 'identity.json'
    src.write_text(identity_text)
    key = run([tool('candidate-probe'), 'schema', 'identity', src, d / 'identity.bin']).stdout.decode().strip()
    return key, identity['main'], doc


results = {}
plain = project('omitted', '')
key_base, main_base, _ = lock('baseline', plain)
key_cand, main_cand, lock_cand = lock('candidate', plain)
assert key_base == key_cand and main_base == main_cand, (key_base, key_cand)
assert '.present(' not in main_cand
results['omitted'] = {'baseline_key': key_base, 'candidate_key': key_cand, 'equal': True, 'main': main_cand,
                      'lock_format': lock_cand['format']}
explicit_false = project('false', 'presentation = false\n')
key_false, main_false, _ = lock('candidate', explicit_false)
assert key_false == key_base and main_false == main_base
results['false'] = {'candidate_key': key_false, 'equal_to_omitted': True}
enabled = project('enabled', 'presentation = true\n')
key_true, main_true, lock_true = lock('candidate', enabled)
assert key_true != key_base and '.present("polars", native_0::present)' in main_true, main_true
results['enabled'] = {'candidate_key': key_true, 'differs': True, 'main': main_true}
# The wrapper generator, through the test-support probe, for both manifest formats.
probe = tool('candidate-probe')
wrappers = {}
for name in ('omitted', 'enabled'):
    out = run([probe, 'wrapper', work / name / 'rnx.toml', work / name]).stdout.decode()
    wrappers[name] = out.split('---')[0]
assert wrappers['omitted'] == main_base and wrappers['enabled'] == main_true
git_omitted = (
    'format = 2\n[application]\nentry = "main.rn"\n[runtime]\ngit = "https://github.com/nilket-com/rnx"\nrev = "b5664ff5400d8dad8c44f39b3c52832d954ab7b1"\n'
    '[native.polars]\ngit = "https://github.com/nilket-com/rnx"\nrev = "b5664ff5400d8dad8c44f39b3c52832d954ab7b1"\npackage = "rnx-polars"\nbuilder = "build"\nhook = "plain"\n')
for name, text in [('git-omitted', git_omitted), ('git-enabled', git_omitted + 'presentation = true\n')]:
    d = work / name
    d.mkdir(exist_ok=True)
    (d / 'rnx.toml').write_text(text)
    wrappers[name] = run([probe, 'wrapper', d / 'rnx.toml', d]).stdout.decode().split('---')[0]
assert '.present(' not in wrappers['git-omitted'] and '.present("polars", native_0::present)' in wrappers['git-enabled']
assert wrappers['git-omitted'].replace('with_lifecycle', 'with') == wrappers['git-omitted']
results['wrappers'] = wrappers
# Every other identity input is unchanged between the omitted and enabled locks.
a = json.loads(json.loads((plain / 'rnx.lock').read_text())['assembly']['identity'])
b = json.loads(json.loads((enabled / 'rnx.lock').read_text())['assembly']['identity'])
changed = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
assert changed == ['main'], changed
results['identity_fields_changed_by_presentation'] = changed
save('identity.json', results)
print(f'identity: omitted key {key_base[:12]} equal across tools; enabled key {key_true[:12]} differs; only `main` changed', flush=True)
