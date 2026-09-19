from common import *
import shutil, tarfile, io
T.mkdir(exist_ok=True)
h=T/'cargo-home';h.mkdir(exist_ok=True)
if not (h/'registry').exists(): (h/'registry').symlink_to(Path.home()/'.cargo/registry',target_is_directory=True)
# Preserve the preliminary discovery separately: final metadata uses this retained location.
a=T/'discovery'
a.mkdir(exist_ok=True);(a/'src').mkdir(exist_ok=True)
manifest='[package]\nname="git-discovery"\nversion="0.0.0"\nedition="2024"\n[workspace]\n[dependencies]\n'+''.join(f'{name}={{git="{URL}",rev="{REV}"}}\n' for name in ['rnx','rnx-polars','rnx-postgres'])
(a/'Cargo.toml').write_text(manifest)
main='fn main() -> Result<(), Box<dyn std::error::Error>> { rnx::main_with(rnx::Extensions::none().with("polars",rnx_polars::build).with_lifecycle("postgres",rnx_postgres::build)) }\n'
(a/'src/main.rs').write_text(main)
if not (a/'Cargo.lock').exists() and (O/'Cargo.lock').exists(): (a/'Cargo.lock').write_bytes((O/'Cargo.lock').read_bytes())
run(['cargo','fetch','--locked','--manifest-path',a/'Cargo.toml'])
m=run(['cargo','metadata','--offline','--locked','--format-version=1','--manifest-path',a/'Cargo.toml'])
(O/'metadata.json').write_bytes(m.stdout)
d=json.loads(m.stdout); pkgs={p['name']:p for p in d['packages'] if p['name'] in ['rnx','rnx-polars','rnx-postgres']}
assert len(pkgs)==3
assert all(p['source'].endswith('#'+REV) for p in pkgs.values())
root=Path(pkgs['rnx']['manifest_path']).parent
assert Path(pkgs['rnx-polars']['manifest_path']).parent==root/'adapters/polars'
assert Path(pkgs['rnx-postgres']['manifest_path']).parent==root/'adapters/postgres'
for name in ('rnx-polars','rnx-postgres'):
    node=next(n for n in d['resolve']['nodes'] if n['id']==pkgs[name]['id'])
    assert any(e['pkg']==pkgs['rnx']['id'] for e in node['deps'])
save('discovery.json',{'revision':REV,'url':URL,'packages':pkgs,'checkout':str(root),'single_runner':True})
(O/'Cargo.lock').write_bytes((a/'Cargo.lock').read_bytes());(O/'Cargo.toml').write_text(manifest);(O/'main.rs').write_text(main)
# A copied product helper preserves the real inventory/audit and fingerprint code.
s=T/'tool'
if not s.exists():
    archive=git(B.parent/'rnx','archive',REV,'tools/project').stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar: tar.extractall(T/'tool-source',filter='data')
    shutil.move(T/'tool-source/tools/project',s)
    src=s/'src/assembly_probe.rs';text=src.read_text();needle='match args.first().and_then(|a| a.to_str()) {'
    text=text.replace(needle,needle+'''\n        Some("audit") if args.len() == 6 => {
            let data=std::fs::read(&args[1]).map_err(|e| e.to_string())?;
            let inv=inventory::native(&data,Path::new(&args[2]),Path::new(&args[3]),Path::new(&args[4]),&mut fingerprint::Allowance::default())?;
            std::fs::write(&args[5],serde_json::to_vec_pretty(&inv).map_err(|e| e.to_string())?).map_err(|e| e.to_string())?;
            Ok(())
        }
        Some("digest") if args.len() == 3 => {
            let data=std::fs::read(&args[1]).map_err(|e| e.to_string())?;
            std::fs::write(&args[2],blake3::hash(&data).to_hex().as_str()).map_err(|e| e.to_string())?;
            Ok(())
        }
''');src.write_text(text)
    f=s/'src/inventory.rs'; text=f.read_text();text=text.replace('let trees = fingerprint::many(roots.into_iter().collect(), allowance)?;', 'let trees = if std::env::var_os("RNX_PROBE_AUDIT_ONLY").is_some() { vec![] } else { fingerprint::many(roots.into_iter().collect(), allowance)? };');f.write_text(text)
    # Archive exact source delta, not just hashes.
    chunks=[]
    import difflib
    for name in ['assembly_probe.rs','inventory.rs']:
        before=git(B.parent/'rnx','show',f'{REV}:tools/project/src/{name}').stdout.decode()
        chunks.extend(difflib.unified_diff(before.splitlines(True),(s/'src'/name).read_text().splitlines(True),fromfile=f'a/tools/project/src/{name}',tofile=f'b/tools/project/src/{name}'))
    (O/'tool.patch').write_text(''.join(chunks))
run(['cargo','build','--offline','--release','--features','test-support','--bin','rnx-project-assembly-probe','--manifest-path',s/'Cargo.toml'],timeout=600)
save('conditions.json',{'root_baseline':REV,'root_head':git(B.parent/'rnx','rev-parse','HEAD').stdout.decode().strip(),'cargo':run(['cargo','-V']).stdout.decode().strip(),'rustc':run(['rustc','-Vv']).stdout.decode(),'cargo_home':str(h),'registry':'shared pre-populated download cache; private git cache','tool_patch':'tool.patch','build_jobs':4})
print('Discovery and inventory helper ready',flush=True)
