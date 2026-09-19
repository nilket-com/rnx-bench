from common import *
assert not T.exists(),'fresh whole target required';T.mkdir();O.mkdir(parents=True,exist_ok=True)
advertised=run(['git','ls-remote',URL,'refs/heads/main']).stdout.decode().strip();assert advertised
save('published-origin.json',{'advertised_main':advertised,'installed_revision':REV})
source=T/'fixture-checkout';origin=T/'fixture-origin.git';run(['git','clone','--quiet','--no-hardlinks',R,source]);git(source,'checkout','--quiet','--detach',REV);run(['git','init','--bare','--quiet',origin]);url=origin.as_uri()
p=source/'Cargo.toml';p.write_text(p.read_text().replace('repository = "https://github.com/nilket-com/rnx"',f'repository = "{url}"'));git(source,'add','Cargo.toml');git(source,'commit','-qm','fixture: private origin for one-install journey');fixture_rev=git(source,'rev-parse','HEAD').stdout.decode().strip();git(source,'push','--quiet',url,'HEAD:refs/heads/main');git(source,'bundle','create',O/'fixture.bundle','HEAD','^'+REV)
# Isolated install cache; registry sources pre-exist, Git acquisitions do not.
home=T/'install-cargo';home.mkdir();(home/'registry').symlink_to(Path.home()/'.cargo/registry',target_is_directory=True)
# The controlled tool PATH contains no rnx-project, nor any other rnx.
tools=T/'tools';tools.mkdir()
for name in ['cargo','rustc','rustup']:(tools/name).symlink_to(shutil.which(name))
for kind,coordinate,rev in [('published',URL,REV),('fixture',url,fixture_rev)]:
 d=T/kind;d.mkdir();env=BASE|{'CARGO_HOME':str(home)};start=time.monotonic()
 r=run(['cargo','install','--git',coordinate,'--rev',rev,'rnx','--locked','--jobs','8','--root',d/'install','--target-dir',T/'install-target'],env=env)
 (O/(kind+'-install.log')).write_bytes(r.stdout+r.stderr);exe=d/'install/bin/rnx';assert sorted(p.name for p in exe.parent.iterdir())==['rnx']
 cargo=d/'cargo';cargo.mkdir();(cargo/'registry').symlink_to(Path.home()/'.cargo/registry',target_is_directory=True)
 e={'PATH':str(exe.parent)+':'+str(tools)+':/usr/bin:/bin','CARGO_HOME':str(cargo),'XDG_STATE_HOME':str(d/"state space'quote"),'XDG_DATA_HOME':str(d/'data'),'RNX_PROJECT_CACHE':str(d/'cache'),'RNX_CONFIG':str(d/'no-config'),'RNX_HISTORY':str(d/'history')}
 assert shutil.which('rnx-project',path=e['PATH']) is None
 data={'origin':coordinate,'rev':rev,'exe':str(exe),'exe_sha256':sha(exe),'install_seconds':time.monotonic()-start,'env':e,'only_installed_binary':'rnx','registry_cache':'preexisting shared registry sources; separate empty consumer Git caches','fixture_source':str(source)}
 (d/'setup.json').write_text(json.dumps(data,indent=2)+'\n');save(kind+'-setup.json',data);print(kind,'single binary installed',flush=True)
source.rename(T/'fixture-checkout-unavailable');assert not source.exists()
save('setup.json',{'published':REV,'fixture':fixture_rev,'fixture_checkout_renamed_before_journeys':True,'source_checkout_available':False,'fixture_manifest_change':'repository URL only'})
