"""The product at PRODUCT archived and built; a bare Git origin with three revisions: the tree,
plus the two 0061-style retained-output natives (an embedding reader and a runtime-configuration
reader whose build script re-runs on a declared environment input), plus a build-script change."""
from common import *
import io, shutil, tarfile
assert not T.exists() and not O.exists()
T.mkdir(); O.mkdir(parents=True)
assert not run(['git', '-c', 'color.ui=false', 'diff', PRODUCT, '--', '.', ':(exclude)plans/**'], cwd=R).stdout
product = T / 'product'
product.mkdir()
with tarfile.open(fileobj=io.BytesIO(run(['git', 'archive', PRODUCT], cwd=R).stdout)) as tar:
    tar.extractall(product, filter='data')
git(product, 'init', '-q'); git(product, 'add', '-A'); git(product, 'commit', '-q', '-m', 'product')
run(['cargo', 'build', '--locked', '--offline', '--release', '--bin', 'rnx'], cwd=product, timeout=1800)
assert RNX.is_file()
bare = T / 'origin.git'
run(['git', 'init', '--bare', '-q', bare])
git(product, 'push', '-q', bare, 'HEAD:refs/heads/main')
rev1 = git(product, 'rev-parse', 'HEAD').stdout.decode().strip()


def native(name, crate, build_rs, lib_rs):
    d = product / 'adapters' / name
    (d / 'src').mkdir(parents=True)
    (d / 'Cargo.toml').write_text(f'[package]\nname = "{crate}"\nversion = "0.0.0"\nedition = "2024"\npublish = false\n[workspace]\n[dependencies]\n'
                                  'rnx = { path = "../..", default-features = false, features = ["count-allocations"] }\n')
    (d / 'build.rs').write_text(build_rs)
    (d / 'src/lib.rs').write_text(lib_rs)


# The embedding reader (0061's shape): the path reaches the executable through env!.
native('probe', 'rnx-probe',
       'fn main() { let p = std::path::PathBuf::from(std::env::var("OUT_DIR").unwrap()).join("retained.txt");'
       ' std::fs::write(&p, "cache-owned retained value").unwrap(); println!("cargo:rustc-env=RETAINED_PATH={}", p.display()); }\n',
       'use rnx::rune;\npub fn build(m: &mut rune::Module) -> Result<Vec<(String, &\'static str)>, String> {\n'
       '    m.function("retained", || -> Result<String, String> { std::fs::read_to_string(env!("RETAINED_PATH")).map_err(|e| format!("{}: {e}", env!("RETAINED_PATH"))) })'
       '.build().map_err(|e| e.to_string())?;\n    Ok(vec![("probe::retained".into(), "retained()")])\n}\n')
# The runtime-configuration reader (the review's counterexample): the build script writes a value
# taken from a declared environment input; the executable learns the file's path at runtime.
native('probe-config', 'rnx-probe-config',
       'fn main() { println!("cargo:rerun-if-env-changed=PROBE_VALUE"); let v = std::env::var("PROBE_VALUE").unwrap_or_else(|_| "first".into());'
       ' let p = std::path::PathBuf::from(std::env::var("OUT_DIR").unwrap()).join("retained.txt"); std::fs::write(&p, v).unwrap(); }\n',
       'use rnx::rune;\npub fn build(m: &mut rune::Module) -> Result<Vec<(String, &\'static str)>, String> {\n'
       '    m.function("retained", || -> Result<String, String> { let p = std::env::var("PROBE_RETAINED_PATH").map_err(|e| e.to_string())?; std::fs::read_to_string(&p).map_err(|e| format!("{p}: {e}")) })'
       '.build().map_err(|e| e.to_string())?;\n    Ok(vec![("probe_config::retained".into(), "retained()")])\n}\n')
git(product, 'add', '-A'); git(product, 'commit', '-q', '-m', 'retained-output natives')
git(product, 'push', '-q', bare, 'HEAD:refs/heads/main')
rev2 = git(product, 'rev-parse', 'HEAD').stdout.decode().strip()
# A third revision changes the embedding reader's build script (the probe's l4 case).
p = product / 'adapters/probe/build.rs'
p.write_text(p.read_text().replace('cache-owned retained value', 'value at the third revision'))
git(product, 'add', '-A'); git(product, 'commit', '-q', '-m', 'build script changed')
git(product, 'push', '-q', bare, 'HEAD:refs/heads/main')
rev3 = git(product, 'rev-parse', 'HEAD').stdout.decode().strip()
git(product, 'checkout', '-q', rev2)  # the path-runtime case uses the tree with both natives
CARGO_HOME.mkdir()
(CARGO_HOME / 'registry').symlink_to(Path.home() / '.cargo/registry', target_is_directory=True)
save('prepare.json', {'product': PRODUCT, 'rnx_sha256': sha(RNX.read_bytes()), 'origin_url': bare.as_uri(), 'origin_rev': rev1, 'probe_rev': rev2, 'changed_rev': rev3})
print('product built; origin with three revisions; private Cargo home', flush=True)
