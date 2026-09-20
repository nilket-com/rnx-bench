"""Matched stock binaries (baseline worktree and the checkout at PRODUCT) and two Polars
projects from the product: one with `presentation = true` as `add` writes it, one with the
field omitted. A large CSV for the bounded-render measurements."""
from common import *
assert not T.exists() and not O.exists()
T.mkdir(); O.mkdir(parents=True)
head = run(['git', 'rev-parse', '--short', 'HEAD']).stdout.decode().strip()
assert head == PRODUCT, head
assert not run(['git', '-c', 'color.ui=false', 'diff', PRODUCT, '--', '.', ':(exclude)README.md', ':(exclude)plans/**']).stdout
save('source.json', {'baseline': BASELINE, 'product': PRODUCT, 'allowed_differences': 'plan/evidence text only'})
run(['git', 'worktree', 'add', '--detach', T / 'before', BASELINE])
for name, source in [('baseline', T / 'before'), ('stock', R)]:
    p = run(['cargo', 'build', '--release', '--locked', '--offline', '--bin', 'rnx', '-j', '8'], cwd=source)
    (O / (name + '-build.log')).write_bytes(p.stdout + p.stderr)
    shutil.copy2(source / 'target/release/rnx', T / name)
save('binaries.json', {k: {'path': str(T / k), 'sha256': sha(T / k), 'size': (T / k).stat().st_size} for k in ['baseline', 'stock']})
# Two projects from the product's own tool, differing only in the declaration field.
projects = {}
for name in ['present', 'plain']:
    project = T / name
    project.mkdir()
    (project / 'main.rn').write_text('pub fn main(_) { 42 }\n')
    (project / 'rnx.toml').write_text(f'format = 1\n[application]\nentry = "main.rn"\n[runtime]\npath = "{R}"\n')
    run([T / 'stock', 'project', 'add', 'polars', '--manifest', project / 'rnx.toml'], cwd=project, timeout=120)
    manifest = (project / 'rnx.toml').read_text()
    assert 'presentation = true' in manifest
    if name == 'plain':
        manifest = manifest.replace('presentation = true\n', '')
        (project / 'rnx.toml').write_text(manifest)
    t0 = time.monotonic()
    run([T / 'stock', 'project', 'lock', '--manifest', project / 'rnx.toml', '--offline'], cwd=project, timeout=600)
    run([T / 'stock', 'project', 'build', '--manifest', project / 'rnx.toml', '--offline'], cwd=project, timeout=1800)
    seconds = round(time.monotonic() - t0, 1)
    wrapper = json.loads(json.loads((project / 'rnx.lock').read_text())['assembly']['identity'])['main']
    assert ('.present("polars", native_0::present)' in wrapper) == (name == 'present'), wrapper
    artifact = artifact_of(project)
    projects[name] = {'manifest': manifest, 'wrapper': wrapper, 'artifact': str(artifact), 'artifact_sha256': sha(artifact),
                      'artifact_size': artifact.stat().st_size, 'lock_build_seconds': seconds}
save('projects.json', projects)
work = T / 'data'
work.mkdir()
(work / 'sales.csv').write_text('region,item,qty,price\nwest,apple,3,1.5\nwest,pear,1,2.0\neast,apple,5,1.5\neast,plum,2,3.0\nnorth,apple,4,1.5\n')
with (work / 'big.csv').open('w') as f:
    f.write(','.join(f'c{i}' for i in range(12)) + '\n')
    for r in range(200_000):
        f.write(','.join(str(r * 12 + c) for c in range(12)) + '\n')
save('data.json', {'sales_bytes': (work / 'sales.csv').stat().st_size, 'big_bytes': (work / 'big.csv').stat().st_size, 'big_rows': 200_000, 'big_columns': 12})
print('matched binaries and both Polars projects ready', flush=True)
