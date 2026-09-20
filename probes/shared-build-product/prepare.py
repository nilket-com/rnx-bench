"""The product at PRODUCT archived and built (stock `rnx`), a bare Git origin of the same tree
with a second revision carrying the 0061 retained-output native, and a private Cargo home."""
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
run(['cargo', 'build', '--locked', '--offline', '--release', '--features', 'test-support', '--bin', 'rnx', '--target-dir', T / 'support-target'], cwd=product, timeout=1800)
assert RNX.is_file() and RNX_SUPPORT.is_file()
# The origin: the product tree at one revision; a second revision adds adapters/probe (0061's retained-output consumer).
bare = T / 'origin.git'
run(['git', 'init', '--bare', '-q', bare])
git(product, 'push', '-q', bare, 'HEAD:refs/heads/main')
rev1 = git(product, 'rev-parse', 'HEAD').stdout.decode().strip()
probe = product / 'adapters' / 'probe'
(probe / 'src').mkdir(parents=True)
(probe / 'Cargo.toml').write_text('[package]\nname = "rnx-probe"\nversion = "0.0.0"\nedition = "2024"\npublish = false\n[workspace]\n[dependencies]\n'
                                  'rnx = { path = "../..", default-features = false, features = ["count-allocations"] }\n')
(probe / 'build.rs').write_text('fn main() { let p = std::path::PathBuf::from(std::env::var("OUT_DIR").unwrap()).join("retained.txt");'
                                ' std::fs::write(&p, "cache-owned retained value").unwrap(); println!("cargo:rustc-env=RETAINED_PATH={}", p.display()); }\n')
(probe / 'src/lib.rs').write_text('use rnx::rune;\npub fn build(m: &mut rune::Module) -> Result<Vec<(String, &\'static str)>, String> {\n'
                                  '    m.function("retained", || -> Result<String, String> { std::fs::read_to_string(env!("RETAINED_PATH")).map_err(|e| format!("{}: {e}", env!("RETAINED_PATH"))) })'
                                  '.build().map_err(|e| e.to_string())?;\n    Ok(vec![("probe::retained".into(), "retained()")])\n}\n')
git(product, 'add', '-A'); git(product, 'commit', '-q', '-m', 'retained-output native')
git(product, 'push', '-q', bare, 'HEAD:refs/heads/main')
rev2 = git(product, 'rev-parse', 'HEAD').stdout.decode().strip()
CARGO_HOME.mkdir()
(CARGO_HOME / 'registry').symlink_to(Path.home() / '.cargo/registry', target_is_directory=True)
save('prepare.json', {'product': PRODUCT, 'rnx_sha256': sha(RNX.read_bytes()), 'rnx_support_sha256': sha(RNX_SUPPORT.read_bytes()), 'origin_url': bare.as_uri(), 'origin_rev': rev1, 'probe_rev': rev2})
print('product built; origin with two revisions; private Cargo home', flush=True)
