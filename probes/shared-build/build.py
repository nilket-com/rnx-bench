"""Assemblies from the product's own tool — Polars (presenting), the same without the field,
Polars + PostgreSQL, seeded variants, and a retained-output native from 0061 — plus their
discriminated-wrapper twins. Records exact package-identity overlap with the runtime's lock."""
from common import *
assert not T.exists() and not O.exists()
T.mkdir(); O.mkdir(parents=True)
# The checkout may be ahead of PRODUCT by plan and review text only.
assert not run(['git', '-c', 'color.ui=false', 'diff', PRODUCT, '--', '.', ':(exclude)README.md', ':(exclude)plans/**']).stdout
save('source.json', {'product': PRODUCT, 'head': run(['git', 'rev-parse', '--short', 'HEAD']).stdout.decode().strip()})
run(['cargo', 'build', '--release', '--locked', '--offline', '--bin', 'rnx', '-j', '8'])
shutil.copy2(R / 'target/release/rnx', T / 'stock')
runtime = lock_packages(R / 'Cargo.lock')
save('runtime-lock.json', {'records': len(runtime), 'names': len({p[0] for p in runtime}), 'sha256': sha(R / 'Cargo.lock')})
# The 0061 retained-output consumer as a real adapter: its build script writes a file to OUT_DIR
# and the extension reads that exact file at runtime.
native = T / 'natives' / 'probe'
(native / 'src').mkdir(parents=True)
(native / 'Cargo.toml').write_text('[package]\nname = "rnx-probe"\nversion = "0.0.0"\nedition = "2024"\npublish = false\n[workspace]\n[dependencies]\n'
                                   f'rnx = {{ path = "{R}", default-features = false, features = ["count-allocations"] }}\n')
(native / 'build.rs').write_text('fn main() { let p = std::path::PathBuf::from(std::env::var("OUT_DIR").unwrap()).join("retained.txt");'
                                 ' std::fs::write(&p, "cache-owned retained value").unwrap(); println!("cargo:rustc-env=RETAINED_PATH={}", p.display()); }\n')
(native / 'src/lib.rs').write_text('use rnx::rune;\npub fn build(m: &mut rune::Module) -> Result<Vec<(String, &\'static str)>, String> {\n'
                                   '    m.function("retained", || -> Result<String, String> { std::fs::read_to_string(env!("RETAINED_PATH")).map_err(|e| format!("{}: {e}", env!("RETAINED_PATH"))) })'
                                   '.build().map_err(|e| e.to_string())?;\n    Ok(vec![("probe::retained".into(), "retained()")])\n}\n')
run(['git', '-C', native, 'init', '-q']); run(['git', '-C', native, 'add', '-A'])
run(['git', '-C', native, '-c', 'user.name=probe', '-c', 'user.email=probe@example', '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'probe native'])
assemblies = {}
specs = [('polars', ['polars'], False, None), ('polars-plain', ['polars'], False, 'plain'), ('polars-seeded', ['polars'], True, None),
         ('both', ['polars', 'postgres'], False, None), ('both-seeded', ['polars', 'postgres'], True, None),
         ('retained', ['polars'], False, 'retained'), ('retained-plain', ['polars'], False, 'retained-plain')]
for name, natives, seeded, variant in specs:
    project = T / 'projects' / name
    project.mkdir(parents=True)
    (project / 'main.rn').write_text('pub fn main(_) { 42 }\n')
    (project / 'rnx.toml').write_text(f'format = 1\n[application]\nentry = "main.rn"\n[runtime]\npath = "{R}"\n')
    run([T / 'stock', 'project', 'add', *natives, '--manifest', project / 'rnx.toml'], cwd=project, timeout=120)
    manifest = (project / 'rnx.toml').read_text()
    if variant in ('plain', 'retained-plain'):
        manifest = manifest.replace('presentation = true\n', '')
    if variant in ('retained', 'retained-plain'):
        manifest += f'\n[native.probe]\npath = "{native}"\npackage = "rnx-probe"\nbuilder = "build"\nhook = "plain"\n'
    (project / 'rnx.toml').write_text(manifest)
    if seeded:
        shutil.copy2(R / 'Cargo.lock', project / 'rnx.Cargo.lock')
    p = run([T / 'stock', 'project', 'lock', '--manifest', project / 'rnx.toml', '--offline'], cwd=project, timeout=600)
    identity = json.loads(json.loads((project / 'rnx.lock').read_text())['assembly']['identity'])
    out = T / 'assemblies' / name
    (out / 'src').mkdir(parents=True)
    (out / 'Cargo.toml').write_text(identity['manifest'])
    (out / 'src/main.rs').write_text(identity['main'])
    shutil.copy2(project / 'rnx.Cargo.lock', out / 'Cargo.lock')
    # The discriminated twin: same wrapper body and lock, package name carrying the digest.
    disc_name, disc_manifest = discriminate(out)
    twin = T / 'assemblies' / (name + '-disc')
    shutil.copytree(out, twin)
    (twin / 'Cargo.toml').write_text(disc_manifest)
    lock_text = (twin / 'Cargo.lock').read_text().replace('name = "rnx-project-app"', f'name = "{disc_name}"', 1)
    (twin / 'Cargo.lock').write_text(lock_text)
    packages = lock_packages(out / 'Cargo.lock')
    assemblies[name] = {'natives': natives, 'seeded': seeded, 'variant': variant, 'lock_seconds': p.seconds, 'discriminated_name': disc_name,
                        'overlap': overlap(runtime, packages), 'main': identity['main']}
    o = assemblies[name]['overlap']
    print(f"{name}: {o['assembly_records']} records, {o['shared_names']} shared names, {o['exact_package_matches']} exact matches, "
          f"{len(o['runtime_identities_missing_from_assembly'])} runtime identities absent", flush=True)
save('assemblies.json', assemblies)
work = T / 'data'
work.mkdir()
print('assemblies generated', flush=True)
