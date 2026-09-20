"""The lifetime sequences: shared executables (runtime-only, Polars, PostgreSQL with a real query,
combined) and the retained-output readers, through later shared builds, a same-revision
build-script re-run on a declared environment input, a build-script change at a new revision,
entry removal and the shared directory's removal."""
from common import *
import importlib.util, shutil
spec = importlib.util.spec_from_file_location('cluster', B / 'probes/postgres/cluster.py')
clustermod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clustermod)
prep = json.loads((O / 'prepare.json').read_text())
url, rev1, rev2, rev3 = prep['origin_url'], prep['origin_rev'], prep['probe_rev'], prep['changed_rev']
SHARED = 'shared_build = true\n'
apps = {}
rows = {'sequence': []}


def build(name, natives, rev, env=None, expect_kind='shared'):
    d = project(name, natives, rev=rev)
    lock, b = lock_and_build(d, env=env)
    err = b.stderr.decode(errors='replace')
    assert b.returncode == 0, (name, err[-2000:])
    i = identity_of(d)
    assert i['context']['build']['kind'] == expect_kind, (name, i['context']['build'])
    apps[name] = {'dir': d, 'exe': artifact_of(d), 'kind': i['context']['build']}
    rows[name] = {'build_seconds': b.seconds, 'compiling_entries': compiling(err), 'kind': i['context']['build']}
    print(f"{name}: {b.seconds} s, {rows[name]['compiling_entries']} entries, {expect_kind}", flush=True)
    return apps[name]


def retained_path(shared_dir, crate='rnx-probe-config'):
    found = sorted(shared_dir.glob(f'release/build/{crate}-*/out/retained.txt'))
    assert len(found) == 1, found
    return found[0]


CONFIGURED_PATH = {}


def observe(label, pg, first=None):
    """Every executable's behaviour now, recorded under `label`. The configured reader keeps the
    path it was first given, so a removed file shows as a missing file, not a missing variable.
    When `first` is given, every supported executable must answer exactly as it did then, and the
    runtime-only executable must evaluate positively."""
    key = apps['polars']['kind']['key']
    if 'path' not in CONFIGURED_PATH:
        CONFIGURED_PATH['path'] = retained_path(CACHE / 'build' / key)
    seen = {}
    for name, a in apps.items():
        assert a['exe'].exists(), f'{name}: executable missing'
        # The worker's working directory is outside the project: its CSV is not project source.
        work = T / 'work' / name
        work.mkdir(parents=True, exist_ok=True)
        seen[name] = behaviour(a['exe'], work, pg_url=pg.url, retained_path=CONFIGURED_PATH['path'])
    ev = run([RNX, 'project', 'eval', '--manifest', apps['runtime']['dir'] / 'rnx.toml', '--', '40 + 2'], cwd=apps['runtime']['dir'], env=env_for()).stdout.decode()
    assert ev.strip().endswith('42'), ev
    seen['runtime']['eval'] = ev.strip()[-2:]
    if first is not None:
        for name in ['runtime', 'polars', 'postgres', 'both']:
            assert seen[name] == first[name], (label, name, seen[name], first[name])
        for name in ['embedding-private', 'path-private']:
            assert seen[name]['retained'] == 'Ok("cache-owned retained value")', (label, name, seen[name])
    rows['sequence'].append({'after': label, 'seen': seen})
    print(f"  after {label}: " + ', '.join(f"{n}={b.get('bare_frame') or b.get('query') or b.get('retained') or b.get('configured') or b.get('eval')}" for n, b in seen.items()), flush=True)
    return seen


polars = [('polars', 'rnx-polars', 'plain', 'presentation = true\n' + SHARED)]
postgres = [('postgres', 'rnx-postgres', 'lifecycle', SHARED)]
with clustermod.Cluster() as pg:
    # Declared shared executables.
    build('runtime', [], rev2)
    build('polars', polars, rev2)
    build('postgres', postgres, rev2)
    build('both', polars + postgres, rev2)
    key = apps['polars']['kind']['key']
    # The runtime-configuration reader, falsely declared: the scan cannot see it, it publishes.
    build('configured', [('probe_config', 'rnx-probe-config', 'plain', SHARED)], rev2)
    # The embedding reader, undeclared: private.
    build('embedding-private', [('probe', 'rnx-probe', 'plain', '')], rev2, expect_kind='private')
    # A path runtime with the embedding reader as a path native: private, as today.
    d = T / 'projects' / 'path-private'
    d.mkdir(parents=True)
    (d / 'main.rn').write_text('pub fn main(_) { 42 }\n')
    (d / 'rnx.toml').write_text(f'format = 1\n[application]\nentry = "main.rn"\n[runtime]\npath = "{T / "product"}"\n\n[native.probe]\npath = "{T / "product/adapters/probe"}"\npackage = "rnx-probe"\nbuilder = "build"\nhook = "plain"\nshared_build = true\n')
    lock, b = lock_and_build(d)
    assert b.returncode == 0, b.stderr.decode(errors='replace')[-1500:]
    pi = identity_of(d)
    assert 'build' not in pi['context'] and pi['format'] == 2, pi.get('context')
    apps['path-private'] = {'dir': d, 'exe': artifact_of(d), 'kind': {'kind': 'private', 'note': 'format-2 path identity, no build kind'}}
    rows['path-private'] = {'build_seconds': b.seconds, 'compiling_entries': compiling(b.stderr.decode(errors='replace')), 'identity_format': pi['format']}
    for name, a in apps.items():
        assert str(CACHE / 'build' / key).encode() not in a['exe'].read_bytes(), f'{name} references the shared directory'
    first = observe('the first builds', pg)
    assert first['runtime']['bare_frame'] is None and first['polars']['bare_frame'] == 'presents'
    assert '42' in (first['postgres']['query'] or '') and '42' in (first['both']['query'] or '') and first['both']['bare_frame'] == 'presents', (first['postgres'], first['both'])
    assert first['configured']['configured'] == 'Ok("first")' and first['embedding-private']['retained'] == 'Ok("cache-owned retained value")' and first['path-private']['retained'] == 'Ok("cache-owned retained value")'
    # 1. A later shared build of another assembly.
    build('polars-plain', [('polars', 'rnx-polars', 'plain', SHARED)], rev2)
    after1 = observe('a later shared build', pg, first)
    # 2. The same revision, a declared environment input changed: the reader's build script re-runs
    # into the same OUT_DIR. A different wrapper forces a build; PROBE_VALUE reaches the build script.
    build('configured-with-polars', [('probe_config', 'rnx-probe-config', 'plain', SHARED)] + polars, rev2, env=env_for({'PROBE_VALUE': 'second'}))
    after2 = observe('a same-revision build-script re-run', pg, first)
    assert after2['configured']['configured'] == 'Ok("second")', 'the documented consequence of a false declaration: the older executable reads the rewritten output'
    # 3. A build-script change at a new revision: a new OUT_DIR; the private readers keep their own.
    build('embedding-changed-private', [('probe', 'rnx-probe', 'plain', '')], rev3, expect_kind='private')
    after3 = observe('a build-script change at a new revision', pg, first)
    assert after3['embedding-changed-private']['retained'] == 'Ok("value at the third revision")' and after3['embedding-private']['retained'] == 'Ok("cache-owned retained value")'
    # 4. Removing an entry leaves the shared directory.
    plain_entry = apps['polars-plain']['exe'].parent.parent.name
    removed = run([RNX, 'cache', 'remove', plain_entry, '--root', CACHE, '--quiescent'])
    assert (CACHE / 'build' / key).is_dir() and not (CACHE / 'entries' / plain_entry).exists()
    del apps['polars-plain']
    after4 = observe('an entry removal', pg, first)
    # 5. Removing the shared directory: refused without acknowledgement, then removed.
    listing = json.loads(run([RNX, 'cache', 'list', '--root', CACHE]).stdout.decode())
    build_row = [r for r in listing['entries'] if r['location'] == 'build'][0]
    refused = run([RNX, 'cache', 'remove', f'build-{key}', '--root', CACHE], check=False)
    assert refused.returncode != 0 and '--quiescent' in refused.stderr.decode(errors='replace')
    removed_build = json.loads(run([RNX, 'cache', 'remove', f'build-{key}', '--root', CACHE, '--quiescent']).stdout.decode().strip().splitlines()[-1])
    assert not (CACHE / 'build' / key).exists()
    after5 = observe('the shared directory removal', pg, first)
    # The falsely declared reader keeps asking for its original path: the file is gone.
    assert after5['configured']['configured'].startswith('Err("') and 'No such file or directory' in after5['configured']['configured'], after5['configured']
    assert str(CONFIGURED_PATH['path']) in after5['configured']['configured']
    rows['removal'] = {'entry_removed': plain_entry[:12], 'listing_before': build_row['metadata'], 'refused_without_quiescent': refused.stderr.decode(errors='replace').strip().splitlines()[-1][:160], 'removed': removed_build}
save('lifetime.json', {k: v for k, v in rows.items()})
print('lifetime: shared executables (runtime, Polars, PostgreSQL query, combined) unchanged through later builds, a re-run, a revision change, entry removal and the directory removal; private readers keep their values; the falsely declared reader shows the documented consequence', flush=True)
