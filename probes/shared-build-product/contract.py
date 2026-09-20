"""The declared contract enforced where it is detectable: the retained-output native declared
shared is refused at publication, naming it, with nothing published; undeclared it builds privately
and works; concurrency: two builders on one directory; a removal racing a builder is refused."""
from common import *
import threading, shutil
url, rev1 = origin()
rev2 = json.loads((O / 'prepare.json').read_text())['probe_rev']
rows = {}
matrix = json.loads((O / 'matrix.json').read_text())
key = matrix['key']
# 1. A false declaration: the scan refuses publication and names the native.
d = project('g-probe-declared', [('probe', 'rnx-probe', 'plain', 'shared_build = true\n')], rev=rev2)
lock, build = lock_and_build(d)
err = build.stderr.decode(errors='replace')
assert build.returncode != 0 and 'shared build refused' in err and 'rnx-probe' in err and 'shared_build' in err, err[-1500:]
i = identity_of(d)
# The exact refused assembly, named by the message: no ready document, no artifact, no project receipt.
refused_entry = Path(re.search(r'cache entry (\S+): shared build refused', err).group(1))
assert refused_entry.parent == CACHE / 'entries' and (refused_entry / 'assembly/Cargo.toml').exists(), refused_entry
assert not (refused_entry / 'ready.json').exists() and not (refused_entry / 'ready.new').exists()
assert not any((refused_entry / 'artifacts').iterdir()) if (refused_entry / 'artifacts').exists() else True
assert not (d / '.rnx/receipt.json').exists(), 'no receipt for a refused build'
launch = run([RNX, 'project', 'run', '--manifest', d / 'rnx.toml'], cwd=d, env=env_for(), check=False)
rows['declared'] = {'refused': True, 'message': err.strip().splitlines()[-1][:300], 'entry': refused_entry.name[:12], 'launch_status': launch.returncode, 'build_kind': i['context']['build']}
assert launch.returncode != 0 and not (d / '.rnx/receipt.json').exists()
# 2. The same native undeclared: private, and it reads its retained value.
d2 = project('h-probe-private', [('probe', 'rnx-probe', 'plain', '')], rev=rev2)
lock, build = lock_and_build(d2)
assert build.returncode == 0, build.stderr.decode(errors='replace')[-1500:]
exe = artifact_of(d2)
b = behaviour(exe, d2)
assert identity_of(d2)['context']['build'] == {'kind': 'private'} and b['retained'] == 'Ok("cache-owned retained value")', b
rows['undeclared'] = {'build_kind': 'private', 'behaviour': b, 'build_seconds': build.seconds}
# 3. Two builders on one shared directory at once: two different wrappers, both publish and behave.
# Two wrappers no earlier case built: Polars + PostgreSQL without presentation, and Polars alone, both at rev2.
p1 = project('i-concurrent-1', [('polars', 'rnx-polars', 'plain', 'shared_build = true\n'), ('postgres', 'rnx-postgres', 'lifecycle', 'shared_build = true\n')], rev=rev2)
p2 = project('j-concurrent-2', [('polars', 'rnx-polars', 'plain', 'shared_build = true\n')], rev=rev2)
for d in (p1, p2):
    run([RNX, 'project', 'lock', '--manifest', d / 'rnx.toml'], cwd=d, env=env_for(), timeout=900)
results = {}
def build(d, tag):
    results[tag] = run([RNX, 'project', 'build', '--manifest', d / 'rnx.toml'], cwd=d, env=env_for(), timeout=3600, check=False)
threads = [threading.Thread(target=build, args=(p1, 'first')), threading.Thread(target=build, args=(p2, 'second'))]
for t in threads: t.start()
for t in threads: t.join()
for tag, d in [('first', p1), ('second', p2)]:
    assert results[tag].returncode == 0, (tag, results[tag].stderr.decode(errors='replace')[-1500:])
rows['concurrent'] = {tag: {'seconds': results[tag].seconds, 'entries': compiling(results[tag].stderr.decode(errors='replace')), 'behaviour': behaviour(artifact_of(d), d)}
                      for tag, d in [('first', p1), ('second', p2)]}
assert rows['concurrent']['first']['behaviour'] == {'bare_frame': 'opaque', 'postgres': True, 'retained': None} and rows['concurrent']['second']['behaviour']['bare_frame'] == 'opaque'
assert rows['concurrent']['first']['entries'] >= 1 and rows['concurrent']['second']['entries'] >= 1, 'both must have compiled'
# 4. A removal racing a builder is refused while the builder holds the lock; listing shows the directory.
p3 = project('k-racing', [('polars', 'rnx-polars', 'plain', 'presentation = true\nshared_build = true\n')] + [('postgres', 'rnx-postgres', 'lifecycle', 'shared_build = true\n')], rev=rev2)
run([RNX, 'project', 'lock', '--manifest', p3 / 'rnx.toml'], cwd=p3, env=env_for(), timeout=900)
holder = subprocess.Popen([str(RNX), 'project', 'build', '--manifest', str(p3 / 'rnx.toml')], cwd=p3, env=env_for(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
# The builder takes its shared hold before it starts Cargo: wait for that Cargo child.
deadline = time.time() + 120
while time.time() < deadline and not run(['pgrep', '-f', f'cargo build .*{CACHE}/entries'], check=False).stdout:
    time.sleep(0.2)
assert holder.poll() is None, 'the builder must still be running'
removal = run([RNX, 'cache', 'remove', f'build-{key}', '--root', CACHE, '--quiescent'], check=False)
busy = removal.stderr.decode(errors='replace')
assert removal.returncode != 0 and 'busy' in busy and f'build-{key}' in busy, busy[-500:]
out, err = holder.communicate(timeout=3600)
assert holder.returncode == 0, err.decode(errors='replace')[-1500:]
assert (CACHE / 'build' / key).is_dir()
dry_live = json.loads(run([RNX, 'cache', 'remove', f'build-{key}', '--root', CACHE, '--dry-run']).stdout.decode())
assert dry_live['entries'][0]['metadata']['kind'] == 'build' and dry_live['entries'][0]['metadata']['referencing_entries'] >= 6, dry_live
listing = json.loads(run([RNX, 'cache', 'list', '--root', CACHE]).stdout.decode())
build_rows = [r for r in listing['entries'] if r['location'] == 'build']
assert len(build_rows) == 1 and build_rows[0]['id'] == f'build-{key}' and build_rows[0]['metadata']['referencing_entries'] >= 6, build_rows
rows['removal'] = {'busy_refusal': busy.strip().splitlines()[-1][:300], 'listing': build_rows[0]['metadata'], 'listing_bytes': build_rows[0]['logical']}
# 4b. An interrupted removal keeps the build kind: the pending directory is listed as build-<key>,
# the bare spelling cannot resume it, a rebuild at the same key makes a fresh directory, resume
# under the proper lock is refused while that builder holds it, and afterwards removes only the
# pending directory.
release = T / 'release-after-rename'
release.unlink(missing_ok=True)
paused = subprocess.Popen([str(RNX_SUPPORT), 'cache', 'remove', f'build-{key}', '--root', str(CACHE), '--quiescent'], env=env_for({'RNX_REMOVE_PAUSE': 'after-rename', 'RNX_REMOVE_RELEASE': str(release)}),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
seen = []
for line in paused.stdout:
    seen.append(line.strip())
    if '"paused":"after-rename"' in line:
        break
assert any('"committed":true' in l for l in seen), seen
pending = CACHE / 'removing' / f'build-{key}'
assert pending.is_dir() and not (CACHE / 'build' / key).exists()
paused.kill(); paused.wait()
listing = json.loads(run([RNX, 'cache', 'list', '--root', CACHE]).stdout.decode())
pending_rows = [r for r in listing['entries'] if r['location'] == 'removing']
assert len(pending_rows) == 1 and pending_rows[0]['id'] == f'build-{key}' and pending_rows[0]['path'] == str(pending) and pending_rows[0]['metadata']['kind'] == 'build', pending_rows
bare = run([RNX, 'cache', 'remove', key, '--root', CACHE, '--resume', '--quiescent'], check=False)
assert bare.returncode != 0 and 'nothing removed' in bare.stderr.decode(errors='replace') and pending.is_dir(), bare.stderr.decode(errors='replace')[-300:]
# Containment names the actual pending component: a resume run from inside it is refused.
inside = run([RNX, 'cache', 'remove', f'build-{key}', '--root', CACHE, '--resume', '--quiescent'], cwd=pending, check=False)
assert inside.returncode != 0 and 'inside target' in inside.stderr.decode(errors='replace') and pending.is_dir(), inside.stderr.decode(errors='replace')[-300:]
dry = json.loads(run([RNX, 'cache', 'remove', f'build-{key}', '--root', CACHE, '--resume', '--dry-run']).stdout.decode())
assert dry['dry_run'] and dry['entries'][0]['id'] == f'build-{key}' and dry['entries'][0]['path'] == str(pending) and dry['entries'][0]['metadata']['kind'] == 'build', dry
p5 = project('m-rebuild-after-interrupted-removal', [], rev=rev2)  # runtime only: a cheap shared build
run([RNX, 'project', 'lock', '--manifest', p5 / 'rnx.toml'], cwd=p5, env=env_for(), timeout=900)
assert identity_of(p5)['context']['build'] == {'kind': 'shared', 'key': key}
rebuild = subprocess.Popen([str(RNX), 'project', 'build', '--manifest', str(p5 / 'rnx.toml')], cwd=p5, env=env_for(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
deadline = time.time() + 120
while time.time() < deadline and not run(['pgrep', '-f', f'cargo build .*{CACHE}/entries'], check=False).stdout:
    time.sleep(0.2)
assert rebuild.poll() is None
resume_busy = run([RNX, 'cache', 'remove', f'build-{key}', '--root', CACHE, '--resume', '--quiescent'], check=False)
assert resume_busy.returncode != 0 and 'busy' in resume_busy.stderr.decode(errors='replace'), resume_busy.stderr.decode(errors='replace')[-300:]
out, err2 = rebuild.communicate(timeout=3600)
assert rebuild.returncode == 0, err2.decode(errors='replace')[-1500:]
assert (CACHE / 'build' / key).is_dir() and pending.is_dir()
resumed = run([RNX, 'cache', 'remove', f'build-{key}', '--root', CACHE, '--resume', '--quiescent'])
assert not pending.exists() and (CACHE / 'build' / key).is_dir(), 'resume removes the pending directory only'
rerun = run([RNX, 'project', 'run', '--manifest', p5 / 'rnx.toml'], cwd=p5, env=env_for()).stdout.decode()
assert rerun.strip().endswith('42')
rows['interrupted_removal'] = {'pending_listed_as': pending_rows[0]['id'], 'bare_resume': bare.stderr.decode(errors='replace').strip().splitlines()[-1][:160],
                               'resume_from_inside': inside.stderr.decode(errors='replace').strip().splitlines()[-1][:160], 'pending_dry_run': dry['entries'][0]['metadata'],
                               'resume_while_building': resume_busy.stderr.decode(errors='replace').strip().splitlines()[-1][:160], 'rebuilt_directory_survives_resume': True,
                               'removed': json.loads(resumed.stdout.decode().strip().splitlines()[-1])}
# 5. User overrides stay refused: an environment override and an unmodelled configuration key.
p4 = project('l-refusals', [('polars', 'rnx-polars', 'plain', 'shared_build = true\n')], rev=rev2)
over = run([RNX, 'project', 'lock', '--manifest', p4 / 'rnx.toml'], cwd=p4, env=env_for({'CARGO_BUILD_BUILD_DIR': str(T / 'elsewhere')}), check=False)
assert over.returncode != 0 and 'CARGO_BUILD_BUILD_DIR' in over.stderr.decode(errors='replace'), over.stderr.decode(errors='replace')[-400:]
home2 = T / 'cargo-home-config'
home2.mkdir(exist_ok=True)
(home2 / 'registry').symlink_to(Path.home() / '.cargo/registry', target_is_directory=True) if not (home2 / 'registry').exists() else None
(home2 / 'config.toml').write_text(f'[build]\nbuild-dir = "{T / "elsewhere"}"\n')
conf = run([RNX, 'project', 'lock', '--manifest', p4 / 'rnx.toml'], cwd=p4, env=env_for({'CARGO_HOME': str(home2)}), check=False)
assert conf.returncode != 0 and 'unsupported Cargo configuration key build' in conf.stderr.decode(errors='replace'), conf.stderr.decode(errors='replace')[-400:]
rows['overrides'] = {'environment': over.stderr.decode(errors='replace').strip().splitlines()[-1][:200], 'configuration': conf.stderr.decode(errors='replace').strip().splitlines()[-1][:200]}
save('contract.json', rows)
print('contract: a false declaration is refused by name with nothing published; undeclared builds privately and works; two builders share one directory; removal is refused while a builder holds the lock; overrides stay refused', flush=True)
