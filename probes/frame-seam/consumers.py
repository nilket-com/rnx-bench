"""Embedding consumers against the candidate: failure-only and panic-only builders compile unchanged;
a runner-only consumer links no presentation code and gains no dependency."""
from common import *
cand = T / 'candidate'
work = T / 'consumers'
work.mkdir(exist_ok=True)
results = {}
sources = {
    'failure-only': 'fn main() { let _ = rnx::Extensions::none().with("fixture", |_| Err("registration failed".into())); }\n',
    'panic-only': 'fn main() { let _ = rnx::Extensions::none().with("fixture", |_| panic!("builder panicked")); }\n',
    'lifecycle-failure-only': 'fn main() { let _ = rnx::Extensions::none().with_lifecycle("fixture", |_, _| Err("no".into())); }\n',
    'runner-only': 'fn main() -> Result<(), Box<dyn std::error::Error>> { rnx::main_with(rnx::Extensions::none()) }\n',
}
for label, source in sources.items():
    c = work / label
    (c / 'src').mkdir(parents=True, exist_ok=True)
    (c / 'src/main.rs').write_text(source)
    (c / 'Cargo.toml').write_text(
        f'[package]\nname="{label}"\nversion="0.0.0"\nedition="2024"\n[workspace]\n[dependencies]\n'
        f'rnx={{path={json.dumps(str(cand))},default-features=false,features=["count-allocations"]}}\n')
    cmd = 'build' if label == 'runner-only' else 'check'
    p = run(['cargo', cmd, '--offline', '--release', '--manifest-path', c / 'Cargo.toml', '--target-dir', work / 'build'], timeout=1800)
    results[label] = {'compiled': True, 'log_tail': p.stderr.decode(errors='replace')[-300:]}
exe = work / 'build/release/runner-only'
symbols = run(['nm', '-C', exe]).stdout.decode(errors='replace')
stock = cand / 'target/release/rnx'
stock_symbols = run(['nm', '-C', stock]).stdout.decode(errors='replace')
# The automatic path consults the (empty) registry, so the lookup is linked into
# every runner; registration itself is only linked when an embedder calls it.
# Symbol names are not stable across inlining, so only the absence of the
# registration entry points is asserted; the lookup's presence is recorded.
lookup = [l for l in symbols.splitlines() if 'Presenters>::present' in l or 'present::Presenters' in l]
registration = [l for l in symbols.splitlines() if 'Presenters>::register' in l or 'Extensions>::present' in l]
assert not registration, registration[:2]
def packages(manifest, extra=()):
    meta = json.loads(run(['cargo', 'metadata', '--manifest-path', manifest, '--offline', '--format-version', '1', *extra]).stdout)
    return sorted({p['name'] for p in meta['packages']})
cand_packages = packages(work / 'runner-only/Cargo.toml')
base_consumer = work / 'runner-only-baseline'
(base_consumer / 'src').mkdir(parents=True, exist_ok=True)
(base_consumer / 'src/main.rs').write_text(sources['runner-only'])
(base_consumer / 'Cargo.toml').write_text((work / 'runner-only/Cargo.toml').read_text().replace(str(cand), str(T / 'baseline')).replace('name="runner-only"', 'name="runner-only-baseline"'))
base_packages = packages(base_consumer / 'Cargo.toml')
cand_deps = sorted(n for n in cand_packages if n != 'runner-only')
base_deps = sorted(n for n in base_packages if n != 'runner-only-baseline')
assert cand_deps == base_deps, sorted(set(cand_deps) ^ set(base_deps))
assert run([exe, 'eval', '42']).stdout == b'42\n'
results['runner-only'].update({'registration_symbols': False, 'lookup_symbols': len(lookup), 'packages_equal_to_baseline': True,
                               'packages': len(cand_packages), 'bytes': exe.stat().st_size})
save('consumers.json', results)
print('failure-only, panic-only and lifecycle builders compile unchanged; runner-only consumer links only the empty-registry lookup', flush=True)
