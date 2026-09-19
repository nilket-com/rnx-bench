from common import *
# New fixture workspace, leaving the historical lock and results untouched.
p=T/'embedding';p.mkdir();files=run(['git','ls-files','probes/extensions'],cwd=B).stdout.decode().splitlines()
for name in files:
 rel=Path(name).relative_to('probes/extensions')
 if rel.parts[0] not in ['src','examples'] and str(rel) not in ['Cargo.toml','Cargo.lock']:continue
 dst=p/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(B/name,dst)
m=p/'Cargo.toml';m.write_text(m.read_text().replace('../../../rnx',str(R)))
r=run(['cargo','build','--release','--offline','-j','4'],cwd=p);(O/'embedding-build.log').write_bytes(r.stderr);shutil.copy2(p/'Cargo.lock',O/'embedding.Cargo.lock')
out=O/'embedding';out.mkdir();r=run(['python3',B/'probes/extensions/check.py',p/'target/release/app'],cwd=B,env=ENV|{'RNX_EXTENSION_RESULTS':str(out)});(out/'driver.log').write_bytes(r.stdout+r.stderr)
symbols=run(['nm','-C',p/'target/release/app']).stdout;assert b'rnx_project::' not in symbols
meta=json.loads(run(['cargo','metadata','--offline','--format-version','1'],cwd=p).stdout);ids={p['id']:p['name'] for p in meta['packages']};active={n['id']:n for n in meta['resolve']['nodes']};assert not any(ids[i]=='rnx-project' for i in active)
# Current standalone server, ordinary binary, actual private PostgreSQL driver.
r=run(['cargo','build','--release','--locked','--offline','--manifest-path','servers/http-postgres/Cargo.toml','--target-dir',T/'server-target','-j','4']);(O/'server-build.log').write_bytes(r.stderr)
source=(B/'probes/server-extraction/normal.py').read_text().replace("out=BENCH/'results/server-extraction-0056/normal'",f'out=pathlib.Path({str(O/"server")!r})').replace("binary=PACKAGE/'target/plain/release/rnx-http-postgres'",f'binary=pathlib.Path({str(T/"server-target/release/rnx-http-postgres")!r})')
# Keep __file__ at the accepted driver's directory for its unchanged imports.
(O/'server-driver.py').write_text(source);code='exec(compile('+repr(source)+','+repr(str(B/'probes/server-extraction/normal.py'))+',"exec"),{"__file__":'+repr(str(B/'probes/server-extraction/normal.py'))+',"__name__":"__main__"})'
r=run(['python3','-c',code],cwd=B);(O/'server-driver.log').write_bytes(r.stdout+r.stderr)
save('smoke.json',{'embedding':{'artifact':str(p/'target/release/app'),'sha256':sha(p/'target/release/app'),'management_symbols':False,'management_in_resolved_graph':False},'server':{'artifact':str(T/'server-target/release/rnx-http-postgres'),'sha256':sha(T/'server-target/release/rnx-http-postgres'),'driver':'ordinary echo, commit, rollback, shutdown, refused test-only registration'}});print('embedding and server smoke passed',flush=True)
