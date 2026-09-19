from common import *
stock=T/'stock';T=T/'roster';T.mkdir()
source=T/'runtime';origin=T/'origin.git';assert not source.exists();run(['git','clone','--quiet','--no-hardlinks',R,source]);run(['git','checkout','--quiet','--detach','1b894e0'],cwd=source)
def git(*args):return run(['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null',*args],cwd=source)
run(['git','init','--bare','--quiet',origin]);url=origin.as_uri()
p=source/'Cargo.toml';p.write_text(p.read_text().replace('repository = "https://github.com/nilket-com/rnx"',f'repository = "{url}"'))
# A complete shipped adapter copy, not an undersized third declaration stub.
paths=git('ls-files','adapters/postgres').stdout.decode().splitlines()
for name in paths:
 src=source/name;dst=source/name.replace('adapters/postgres/','adapters/third/',1);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
p=source/'adapters/third/Cargo.toml';p.write_text(p.read_text().replace('name = "rnx-postgres"','name = "rnx-third"'))
p=source/'adapters/third/src/lib.rs';p.write_text(p.read_text().replace('"postgres::query"','"third::query"'))
git('add','.');git('commit','-qm','fixture: matched three-adapter Git and path roster');rev=git('rev-parse','HEAD').stdout.decode().strip();git('push','--quiet',url,'HEAD:refs/heads/main');git('bundle','create',O/'roster.bundle','HEAD','^1b894e0')
cargo=T/'cargo';cargo.mkdir();(cargo/'registry').symlink_to(Path.home()/'.cargo/registry',target_is_directory=True)
env=ENV|{'CARGO_HOME':str(cargo),'RNX_PROJECT_CACHE':str(T/'cache')};save('roster-env.json',{k:v for k,v in env.items() if k in {'RNX_HISTORY', 'RNX_CONFIG', 'CARGO_HOME', 'PATH', 'PYTHONDONTWRITEBYTECODE', 'RNX_PROJECT_CACHE', 'POLARS_MAX_THREADS', 'TERM', 'LC_ALL', 'LC_CTYPE', 'LANG', 'NO_COLOR', 'HOME'}})
rows=[]
for kind in ['git','path']:
 for n in range(4):
  d=T/f'{kind}-{n}';d.mkdir();m=d/'rnx.toml';(d/'entry.rn').write_text('pub fn main(_) { println!("42"); }\n')
  coord=f'git={json.dumps(url)}\nrev="{rev}"\n' if kind=='git' else f'path={json.dumps(str(source))}\n'
  text=f'format={2 if kind=="git" else 1}\n[application]\nentry="entry.rn"\n[runtime]\n'+coord
  for name in ['polars','postgres','third'][:n]:
   native=coord if kind=='git' else f'path={json.dumps(str(source/"adapters"/name))}\n'
   text+=f'\n[native.{name}]\n'+native+f'package="rnx-{name}"\nbuilder="build"\nhook="'+('plain' if name=='polars' else 'lifecycle')+'"\n'
  m.write_text(text)
  timings={}
  for command in ['lock','build']:
   start=time.monotonic();p=run([stock,'project',command,'--offline','--manifest',m],env=env,ok=False)
   if p.returncode and kind=='git' and n==0 and command=='lock':
    # The deliberately empty Git cache needs one online local-origin acquisition.
    (O/'first-offline-miss.log').write_bytes(p.stdout+p.stderr);start=time.monotonic();p=run([stock,'project','lock','--manifest',m],env=env)
   assert p.returncode==0,p.stderr.decode(errors='replace')
   timings[command]=time.monotonic()-start;(O/f'{kind}-{n}-{command}.log').write_bytes(p.stdout+p.stderr)
  receipt=json.loads((d/'.rnx/receipt.json').read_text());a=Path(env['RNX_PROJECT_CACHE'])/'entries'/receipt['assembly_key']/'artifacts'/receipt['executable_blake3']
  assert run([stock,'project','eval','--manifest',m,'--','42'],env=env).stdout==b'42\n'
  row={'kind':kind,'count':n,'manifest':str(m),'artifact':str(a),'key':receipt['assembly_key'],'sha256':sha(a),'seconds':timings,'bytes':a.stat().st_size};rows.append(row);save('roster.json',rows);print('built',kind,n,timings,flush=True)
# Whole source snapshot and one complete copied PostgreSQL adapter are retained.
save('roster-source.json',{'base':'1b894e0','fixture_revision':rev,'url':url,'source':str(source),'third':'complete tracked PostgreSQL adapter with package and registered help namespace renamed','tracked_files':len(git('ls-files').stdout.decode().splitlines())})
