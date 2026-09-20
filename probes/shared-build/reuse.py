"""Compiler reuse across assemblies. Every build is the tool's exact command into a fresh target
directory; the shared build directory is always the one canonical path, restored from a snapshot
before each alternative. Behaviour of every executable is verified through the worker."""
from common import *
assemblies = json.loads((O / 'assemblies.json').read_text())
cases = []


def build(case, assembly, shared=False, note='', relocated=None):
    src = T / 'assemblies' / assembly
    work = T / 'builds' / case
    shutil.copytree(src, work)
    target = work / 'target'
    args = ['cargo', 'build', '--locked', '--offline', '--release', '--target-dir', target]
    build_dir = relocated or (SHARED if shared else None)
    if build_dir:
        args += ['--config', f'build.build-dir="{build_dir}"']
    p = run(args, cwd=work, timeout=3600)
    err = p.stderr.decode(errors='replace')
    entries = compiling(err)
    (O / f'build-{case}.log').write_text(err)
    exes = [e for e in (target / 'release').iterdir() if e.is_file() and e.name.startswith('rnx-') and not e.suffix]
    assert len(exes) == 1, exes
    exe = exes[0]
    row = {'case': case, 'assembly': assembly, 'build_dir': str(build_dir) if build_dir else None, 'seconds': p.seconds,
           'compiling_entries': len(entries), 'entry_names': [u[0] for u in entries], 'exe': exe.name, 'exe_sha256': sha(exe),
           'behaviour': behaviour(exe, work), 'note': note}
    cases.append(row)
    save('reuse.json', cases)
    print(f"{case}: {p.seconds} s, {len(entries)} entries, {row['behaviour']}", flush=True)
    return row


SHARED.mkdir(parents=True, exist_ok=True)
# Control: today, private directories.
build('a-polars-private', 'polars', note='today: cold, private')
build('b-plain-private', 'polars-plain', note='today: same natives, different wrapper, cold again')
# The wrong-binary control, preserved: undiscriminated wrappers in the shared directory.
build('c-polars-shared', 'polars', shared=True, note='shared: cold')
snapshot('after-c')
build('d-plain-shared', 'polars-plain', shared=True, note='shared: warm after c; the wrong-binary control')
# Relocation control: the same warm state at a different absolute path.
relocated = T / 'builds' / 'relocated-copy'
run(['cp', '-a', SNAPSHOTS / 'after-c', relocated], cwd=T)
build('d2-plain-relocated', 'polars-plain', relocated=relocated, note='warm state copied to another path (relocation control)')
# The discriminated wrappers, both orders, repeats, then PostgreSQL.
shutil.rmtree(SHARED); SHARED.mkdir()
build('w1-present-disc', 'polars-disc', shared=True, note='discriminated: cold')
build('w2-plain-disc', 'polars-plain-disc', shared=True, note='discriminated: plain after present')
build('w3-present-disc-again', 'polars-disc', shared=True, note='discriminated: present again')
build('w4-plain-disc-again', 'polars-plain-disc', shared=True, note='discriminated: plain again')
snapshot('after-w4')
build('w5-both-disc', 'both-disc', shared=True, note='discriminated: PostgreSQL added, unseeded lock')
restore('after-w4')
build('w6-both-seeded-disc-mixed', 'both-seeded-disc', shared=True, note='discriminated: seeded combined into an unseeded directory')
# Seeded throughout: seeded Polars, then seeded combined.
shutil.rmtree(SHARED); SHARED.mkdir()
build('s1-polars-seeded-disc', 'polars-seeded-disc', shared=True, note='seeded: cold')
build('s2-both-seeded-disc', 'both-seeded-disc', shared=True, note='seeded: PostgreSQL added, seeded lock')
# Reverse order of the wrapper pair, from empty: plain first.
shutil.rmtree(SHARED); SHARED.mkdir()
build('r1-plain-disc-first', 'polars-plain-disc', shared=True, note='discriminated: plain first, cold')
build('r2-present-disc-second', 'polars-disc', shared=True, note='discriminated: present second')
# Install to first Polars, at the canonical path the installation wrote.
restore('after-install')
build('g-polars-after-install', 'polars-disc', shared=True, note='after the installation: unseeded')
restore('after-install')
build('h-polars-seeded-after-install', 'polars-seeded-disc', shared=True, note='after the installation: seeded')
sizes = {'shared_after_w4_bytes': bytes_under(SNAPSHOTS / 'after-w4'), 'install_bytes': bytes_under(SNAPSHOTS / 'after-install'),
         'private_polars_target_bytes': bytes_under(T / 'builds' / 'a-polars-private' / 'target')}
save('reuse-sizes.json', sizes)
print('reuse cases complete', flush=True)
