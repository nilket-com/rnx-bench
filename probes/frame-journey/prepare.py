"""Archive the product at PRODUCT_REV, build the stock `rnx` and the kernel, and author,
lock and build one Polars project with the tool's own `add`."""
from common import *
import time
assert not T.exists(), f'{T} exists; remove or move it first'
assert not O.exists(), f'{O} exists; remove or move it first'
T.mkdir(parents=True)
PRODUCT.mkdir()
archive = run(['git', '-C', R, 'archive', PRODUCT_REV], timeout=120).stdout
run(['tar', '-x', '-C', PRODUCT], input=archive)
# The tool fingerprints a path runtime from its Git-tracked files: the archive
# becomes a repository of its own, committed without signing.
run(['git', '-C', PRODUCT, 'init', '-q'])
run(['git', '-C', PRODUCT, 'add', '-A'])
run(['git', '-C', PRODUCT, '-c', 'user.name=probe', '-c', 'user.email=probe@example', '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', f'rnx {PRODUCT_REV}'])
t0 = time.time()
run(['cargo', 'build', '--locked', '--offline', '--release'], cwd=PRODUCT, timeout=1800)
run(['cargo', 'build', '--locked', '--offline', '--release'], cwd=PRODUCT / 'jupyter', timeout=1800)
built = round(time.time() - t0, 1)
assert RNX.is_file() and KERNEL.is_file()
project = T / 'project'
project.mkdir()
(project / 'main.rn').write_text('pub fn main(_) { 42 }\n')
(project / 'rnx.toml').write_text(f'format = 1\n[application]\nentry = "main.rn"\n[runtime]\npath = "{PRODUCT}"\n')
cache = T / 'cache'
env = dict(ENV, RNX_PROJECT_CACHE=str(cache))
run([RNX, 'project', 'add', 'polars', '--manifest', project / 'rnx.toml'], env=env, timeout=120)
manifest = (project / 'rnx.toml').read_text()
assert 'presentation = true' in manifest.split('[native.polars]', 1)[1], manifest
t1 = time.time()
run([RNX, 'project', 'lock', '--manifest', project / 'rnx.toml', '--offline'], env=env, timeout=600)
run([RNX, 'project', 'build', '--manifest', project / 'rnx.toml', '--offline'], env=env, timeout=1800)
project_seconds = round(time.time() - t1, 1)
lock = json.loads((project / 'rnx.lock').read_text())
wrapper = json.loads(lock['assembly']['identity'])['main']
assert '.present("polars", native_0::present)' in wrapper, wrapper
artifact = Path(lock['assembly']['artifact']) if 'artifact' in lock['assembly'] else None
save('prepare.json', {'product_rev': PRODUCT_REV, 'rnx_sha256': sha(RNX.read_bytes()), 'kernel_sha256': sha(KERNEL.read_bytes()),
                      'product_build_seconds': built, 'project_seconds': project_seconds, 'manifest': manifest, 'wrapper': wrapper,
                      'lock_assembly_keys': sorted(lock['assembly'].keys())})
print(f'product {PRODUCT_REV} built ({built} s); Polars project authored by add, locked and built ({project_seconds} s)', flush=True)
