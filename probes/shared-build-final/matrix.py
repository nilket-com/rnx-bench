"""The cost matrix, baseline against product, interleaved: three repeats, each in a fresh cache,
alternating which binary goes first. Every project is authored by the binary's own `add` on a Git
runtime (the product writes `shared_build = true`; the baseline cannot). Every executable's
behaviour is verified through the worker. Storage is measured after each repeat."""
from common import *
import re, statistics as st
origin = json.loads((O / 'origin.json').read_text())
url, rev = origin['url'], origin['rev']
bins = {'before': T / 'baseline', 'after': T / 'stock'}
journal = O / 'matrix-samples.jsonl'
assert not journal.exists()
rows = []


def record(x):
    rows.append(x)
    with journal.open('a') as f:
        f.write(json.dumps(x) + '\n')


def project(root, name, natives, plain=False):
    d = root / name
    d.mkdir(parents=True)
    (d / 'main.rn').write_text('pub fn main(_) { 42 }\n')
    (d / 'rnx.toml').write_text(f'format = 2\n[application]\nentry = "main.rn"\n[runtime]\ngit = "{url}"\nrev = "{rev}"\n')
    return d


def step(kind, exe, cache, d, natives, label, repeat, plain=False):
    env = dict(ENV, RNX_PROJECT_CACHE=str(cache), RNX_HISTORY=str(cache / 'history'), RNX_CONFIG=str(cache / 'no-config'))
    run([exe, 'project', 'add', *natives, '--manifest', d / 'rnx.toml'], cwd=d, env=env, timeout=120)
    if plain:
        (d / 'rnx.toml').write_text((d / 'rnx.toml').read_text().replace('presentation = true\n', ''))
    lock = run([exe, 'project', 'lock', '--manifest', d / 'rnx.toml'], cwd=d, env=env, timeout=900)
    build = run([exe, 'project', 'build', '--manifest', d / 'rnx.toml'], cwd=d, env=env, timeout=3600)
    err = build.stderr.decode(errors='replace')
    entries = len(re.findall(r'^\s*Compiling ', err, re.M))
    identity = json.loads(json.loads((d / 'rnx.lock').read_text())['assembly']['identity'])
    build_kind = identity['context'].get('build', {'kind': 'none (identity 3)'})
    behaviour = bare_frame(artifact_of(d, cache), cache / 'work' / label)
    record({'repeat': repeat, 'kind': kind, 'step': label, 'lock_s': lock.seconds, 'build_s': build.seconds, 'entries': entries, 'build_kind': build_kind, 'behaviour': behaviour})
    print(f'  repeat {repeat} {kind} {label}: lock {lock.seconds} s, build {build.seconds} s, {entries} entries, {build_kind.get("kind")}, {behaviour}', flush=True)


def sequence(kind, repeat):
    cache = T / f'cache-{repeat}-{kind}'
    root = T / f'projects-{repeat}-{kind}'
    exe = bins[kind]
    step(kind, exe, cache, project(root, 'first', ['polars']), ['polars'], 'first-polars', repeat)
    step(kind, exe, cache, project(root, 'plain', ['polars']), ['polars'], 'second-wrapper', repeat, plain=True)
    step(kind, exe, cache, project(root, 'both', ['polars', 'postgres']), ['polars', 'postgres'], 'plus-postgres', repeat)
    step(kind, exe, cache, project(root, 'again', ['polars']), ['polars'], 'attach', repeat)
    size = {'entries': sum(f.stat().st_size for f in (cache / 'entries').rglob('*') if f.is_file()),
            'build': sum(f.stat().st_size for f in (cache / 'build').rglob('*') if f.is_file()) if (cache / 'build').exists() else 0}
    record({'repeat': repeat, 'kind': kind, 'step': 'storage', 'bytes': size})
    print(f'  repeat {repeat} {kind} storage: entries {size["entries"] / 1e9:.2f} GB, shared {size["build"] / 1e9:.2f} GB', flush=True)


for repeat in range(3):
    order = ['before', 'after'] if repeat % 2 == 0 else ['after', 'before']
    for kind in order:
        sequence(kind, repeat)
summary = {}
for label in ['first-polars', 'second-wrapper', 'plus-postgres', 'attach']:
    summary[label] = {}
    for kind in bins:
        v = sorted(x['build_s'] for x in rows if x['kind'] == kind and x['step'] == label)
        e = sorted(x['entries'] for x in rows if x['kind'] == kind and x['step'] == label)
        summary[label][kind] = {'build_s': v, 'median_s': st.median(v), 'entries': e}
    summary[label]['saved_s'] = round(summary[label]['before']['median_s'] - summary[label]['after']['median_s'], 1)
storage = {kind: {k: st.median(x['bytes'][k] for x in rows if x['kind'] == kind and x['step'] == 'storage') for k in ['entries', 'build']} for kind in bins}
# Every recorded row, every repeat: not a dictionary keyed by step that keeps only the last.
for x in rows:
    if 'behaviour' not in x:
        continue
    expected = 'opaque' if x['step'] == 'second-wrapper' else 'presents'
    assert x['behaviour']['bare_frame'] == expected and x['behaviour']['postgres'] == (x['step'] == 'plus-postgres'), (x['repeat'], x['kind'], x['step'], x['behaviour'])
assert sum(1 for x in rows if 'behaviour' in x) == 3 * 2 * 4
after_kinds = {x['build_kind'].get('kind') for x in rows if x['kind'] == 'after' and 'build_kind' in x}
assert after_kinds == {'shared'}, after_kinds
save('matrix-summary.json', {'summary': summary, 'storage_median_bytes': storage, 'repeats': 3})
print(json.dumps({k: {kk: (vv['median_s'] if isinstance(vv, dict) else vv) for kk, vv in v.items()} for k, v in summary.items()}, indent=1), flush=True)
