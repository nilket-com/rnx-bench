"""The cost matrix through the stock binary, every executable's behaviour verified: first Polars
(shared), the same natives with another wrapper, Polars + PostgreSQL, a runtime revision bump, the
relock back; a private control; and the seed lock's effect on resolution."""
from common import *
import shutil
url, rev1 = origin()
rev2 = json.loads((O / 'prepare.json').read_text())['probe_rev']
polars = lambda extra='': [('polars', 'rnx-polars', 'plain', 'presentation = true\nshared_build = true\n' + extra)]
rows = {}


def case(name, d, note):
    lock, build = lock_and_build(d)
    err = build.stderr.decode(errors='replace')
    assert build.returncode == 0, (name, err[-2000:])
    i = identity_of(d)
    exe = artifact_of(d)
    ready = json.loads((exe.parent.parent / 'ready.json').read_text())
    rows[name] = {'lock_seconds': lock.seconds, 'build_seconds': build.seconds, 'compiling_entries': compiling(err), 'build': i['context']['build'],
                  'wrapper': re.search(r'^name = "([^"]+)"', i['manifest'], re.M).group(1)[:24], 'entry': exe.parent.parent.name[:12],
                  'behaviour': behaviour(exe, d), 'ready_format': ready['format'], 'note': note}
    print(f"{name}: lock {lock.seconds} s, build {build.seconds} s, {rows[name]['compiling_entries']} entries, {rows[name]['build']['kind']}, {rows[name]['behaviour']}", flush=True)
    return rows[name]


a = case('a-polars-shared', project('a', polars()), 'first Polars, declared: cold shared')
key = a['build']['key']
assert a['build']['kind'] == 'shared' and (CACHE / 'build' / key).is_dir() and (CACHE / 'locks' / f'build-{key}.lock').is_file()
assert a['behaviour']['bare_frame'] == 'presents'
b = case('b-polars-plain-shared', project('b', [('polars', 'rnx-polars', 'plain', 'shared_build = true\n')]), 'same natives, another wrapper')
assert b['build'] == a['build'] and b['behaviour']['bare_frame'] == 'opaque' and b['compiling_entries'] <= 2, b
c = case('c-both-shared', project('c', polars() + [('postgres', 'rnx-postgres', 'lifecycle', 'shared_build = true\n')]), 'PostgreSQL added')
assert c['build'] == a['build'] and c['behaviour'] == {'bare_frame': 'presents', 'postgres': True, 'retained': None}
d = case('d-polars-shared-rev2', project('d', polars(), rev=rev2), 'runtime revision bump (same sources plus a directory)')
assert d['build'] == a['build'] and d['behaviour']['bare_frame'] == 'presents'
e = case('e-polars-shared-again', project('e', polars()), 'the first declaration again: attaches, builds nothing')
assert e['entry'] == a['entry'] and e['compiling_entries'] == 0 and e['build_seconds'] < 5, e
f = case('f-polars-private', project('f', [('polars', 'rnx-polars', 'plain', 'presentation = true\n')]), 'undeclared: private, as today')
assert f['build'] == {'kind': 'private'} and f['compiling_entries'] >= 300 and f['behaviour']['bare_frame'] == 'presents'
# The seed lock: a fresh project's resolution against the runtime's own lock.
runtime_lock = lock_packages(T / 'product' / 'Cargo.lock')
assembly = lock_packages(T / 'projects' / 'a' / 'rnx.Cargo.lock')
shared_names = {p[0] for p in runtime_lock} & {p[0] for p in assembly}
exact = {p for p in assembly if p in runtime_lock}
seed = {'runtime_records': len(runtime_lock), 'assembly_records': len(assembly), 'shared_names': len(shared_names), 'exact_matches': len(exact),
        'runtime_identities_absent': sorted(f'{n} {v}' for n, v, _ in runtime_lock if n in shared_names and (n, v, _) not in assembly)}
assert seed['exact_matches'] >= 210, seed
sizes = {'shared_bytes': sum(f.stat().st_size for f in (CACHE / 'build' / key).rglob('*') if f.is_file()),
         'entries': {n: sum(f.stat().st_size for f in (CACHE / 'entries' / n).rglob('*') if f.is_file()) for n in os.listdir(CACHE / 'entries')}}
save('matrix.json', {'cases': rows, 'seed': seed, 'sizes': sizes, 'key': key})
print('matrix: declared assemblies share one directory; second wrapper, PostgreSQL, a revision bump and reattachment as measured; private control unchanged; seeded resolution matches the runtime lock', flush=True)
