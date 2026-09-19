from common import *
import shutil
T.mkdir(exist_ok=True);h=T/'cargo-home';h.mkdir(exist_ok=True)
if not (h/'registry').exists():(h/'registry').symlink_to(Path.home()/'.cargo/registry',target_is_directory=True)
s=T/'source';origin=T/'origin.git'
assert not s.exists(),'fresh target required'
run(['git','clone','--quiet','--no-hardlinks',R,s]);git(s,'checkout','--quiet','--detach',BASE)
run(['git','init','--bare','--quiet',origin]);url=origin.as_uri()
c=s/'Cargo.toml';v=c.read_text().replace('default = ["count-allocations"]','default = ["count-allocations", "stock-management"]\nstock-management = ["dep:rnx-project"]')
v=v.replace('[workspace]','[workspace]\nexclude = ["tools/project"]')
v=v.replace('[dependencies]\n','[dependencies]\nrnx-project = { path = "tools/project", optional = true }\n',1).replace('repository = "https://github.com/nilket-com/rnx"',f'repository = "{url}"');c.write_text(v)
shutil.copyfile(P/'files/build.rs',s/'build.rs');shutil.copyfile(P/'files/main.rs',s/'src/main.rs')
lib=s/'tools/project/src/lib.rs';decl=(s/'tools/project/src/main.rs').read_text().split('fn main()')[0]
lib.write_text(decl+'''\n#[cfg(test)] mod tests;
/// Private prototype boundary, not an embedding API promise.
#[inline(never)]
pub fn dispatch(args: Vec<std::ffi::OsString>) -> Result<(), String> { workflow::cli(args) }
pub fn failure_status() -> i32 { if commands::interrupted() { commands::signal_status() } else { 1 } }
''')
(s/'tools/project/src/main.rs').write_text('fn main(){if let Err(e)=rnx_project::dispatch(std::env::args_os().skip(1).collect()){eprintln!("rnx-project: {e}");std::process::exit(rnx_project::failure_status());}}\n')
for name in ['polars','postgres']:
 f=s/'adapters'/name/'Cargo.toml';text=f.read_text().replace('rnx = { path = "../.." }','rnx = { path = "../..", default-features = false, features = ["count-allocations"] }');assert text!=f.read_text();f.write_text(text)
f=s/'tools/project/src/generate.rs';v=f.read_text().replace('path: String,','path: String,\n    #[serde(rename="default-features")]\n    default_features: bool,',1).replace('package: None,','package: None,\n default_features: false,').replace('features: vec!["project-sources".into()],','features: vec!["count-allocations".into(), "project-sources".into()],').replace('package: Some(native.package.clone()),','package: Some(native.package.clone()),\n default_features: true,');f.write_text(v)
run(['cargo','fmt','--manifest-path',s/'Cargo.toml']);run(['cargo','fmt','--manifest-path',s/'tools/project/Cargo.toml'])
run(['cargo','generate-lockfile','--offline','--manifest-path',s/'Cargo.toml'])
git(s,'add','Cargo.toml','Cargo.lock','build.rs','src/main.rs','tools/project/src/lib.rs','tools/project/src/main.rs','tools/project/src/generate.rs','adapters/polars/Cargo.toml','adapters/postgres/Cargo.toml')
git(s,'-c','user.name=Probe','-c','user.email=probe@example.invalid','commit','--quiet','-m','fixture: stock management crate and coordinates')
a=git(s,'rev-parse','HEAD').stdout.decode().strip();(O/'prototype.patch').write_bytes(git(s,'diff',BASE,a).stdout)
# Fetchable revision two has the same code, distinct tracked content.
with (s/'README.md').open('a') as f:f.write('\nGate-1 fixture revision two.\n')
git(s,'add','README.md');git(s,'-c','user.name=Probe','-c','user.email=probe@example.invalid','commit','--quiet','-m','fixture: second acquired revision')
b=git(s,'rev-parse','HEAD').stdout.decode().strip();git(s,'push','--quiet',url,'HEAD:refs/heads/main')
git(s,'bundle','create',O/'fixture.bundle','HEAD','^94f5f3f');git(s,'checkout','--quiet','--detach',a)
save('setup.json',{'baseline':BASE,'rev1':a,'rev2':b,'url':url,'source':str(s),'cargo':run(['cargo','-V']).stdout.decode(),'rustc':run(['rustc','-Vv']).stdout.decode(),'notes':'fixture origin only; registry pre-populated; prototype.patch plus bundle preserve exact sources'})
print('Fixture origin ready',flush=True)
# Actual Cargo installation; only rnx is selected for installation.
p=run(['cargo','install','--git',url,'--rev',a,'rnx','--locked','--root',T/'install-git1','--target-dir',T/'build-target'],timeout=1200)
(O/'install-git1.stderr').write_bytes(p.stderr)
exe=T/'install-git1/bin/rnx';row=json.loads(run([exe,'--probe-coordinates']).stdout);save('first-install.json',row)
assert row['state']=='acquired',row
assert sorted(p.name for p in (T/'install-git1/bin').iterdir())==['rnx']
p=run([exe,'project','adapters']);(O/'adapters.stdout').write_bytes(p.stdout);assert b'polars' in p.stdout and b'postgres' in p.stdout
print('Actual Git install and integrated management pass',flush=True)
