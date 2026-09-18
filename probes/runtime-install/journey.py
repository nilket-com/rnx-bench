"""Rename the fixture checkout, then exercise stock :dep using installed sources only."""
from pathlib import Path
import subprocess as sp, os, json, hashlib, shutil, tomllib, sys
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/runtime-install-0064';T=W/'bin/rnx-project';C=W/'original'
sys.dont_write_bytecode=True
assert C.is_dir() and not (W/'unavailable-original').exists()
env={k:v for k,v in os.environ.items() if not k.startswith('GIT_') and k not in ['RNX_DEP_RUNTIME','RNX_INTERNAL_DEP_ASSOCIATION']}
env.update(TERM='xterm-256color',POLARS_MAX_THREADS='1',PYTHONDONTWRITEBYTECODE='1',RNX_PROJECT_TOOL=str(T),RNX_PROJECT_CACHE=str(W/'cache'),RNX_CONFIG=str(W/'absent-settings'),XDG_STATE_HOME=str(W/"state ' private"),XDG_DATA_HOME=str(W/'data'))
def call(args,e=env,cwd=W):
 p=sp.run(list(map(str,args)),cwd=cwd,env=e,capture_output=True,text=True,timeout=120)
 assert p.returncode==0,(args,p.stdout,p.stderr)
 return p.stdout
def probe(*args):return json.loads(call([T,'runtime-probe',*args]))
source=probe('fingerprint',C);store=Path(env['XDG_DATA_HOME'])/'rnx/runtimes'
doc=probe('install',C,store);I=store/'entries'/doc['id']/'source';installed=probe('fingerprint',I)
assert source['sha256']==installed['sha256'] and source['files']==installed['files'];assert not doc['dirty_tracked']
assert (I/'adapters/polars/src/lib.rs').is_file() and (I/'adapters/postgres/src/lib.rs').is_file()
# Same cache root, same adapter recipe: only native location changes.
identities={};keyenv=dict(env,RNX_PROJECT_CACHE=str(W/'identity-cache'))
for name,root in [('source',C),('installed',I)]:
 p=W/('identity-'+name);p.mkdir();m=p/'rnx.toml';(p/'main.rn').write_text('pub fn main(_) { 42 }')
 m.write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath='+json.dumps(str(root))+'\n')
 call([T,'add','polars','postgres','--manifest',m],e=keyenv)
 call([T,'lock','--offline','--manifest',m],e=keyenv)
 lock=json.loads((p/'rnx.lock').read_text());(O/(name+'-lock.json')).write_text(json.dumps(lock,indent=2)+'\n')
 identities[name]=lock['assembly']
assert identities['source']!=identities['installed']
# Rename physically: every old absolute path stops resolving before first assembly build.
C.rename(W/'unavailable-original');assert not C.exists();assert not (W/'cache').exists()
# Verify all independent objects remain usable with the source gone.
git=I/'.git';assert git.is_dir() and not git.is_symlink()
for rel in ['objects/info/alternates','commondir','gitdir']:assert not (git/rel).exists()
assert 'worktree' not in (git/'config').read_text().lower()
assert probe('fingerprint',I)['sha256']==source['sha256']
env['RNX_INSTALLED_RUNTIME']=str(I) # Fixture selector only; product never reads this variable.
(W/'env.json').write_text(json.dumps(env,indent=2)+'\n')
(O/'installation.json').write_text(json.dumps(doc,indent=2)+'\n')
(O/'snapshot.json').write_text(json.dumps({'source':str(C),'renamed_to':str(W/'unavailable-original'),'installed':str(I),'source_sha256':source['sha256'],'installed_sha256':installed['sha256'],'files':len(source['files']),'bytes':sum(f['bytes'] for f in source['files']),'runtime_override_absent':'RNX_DEP_RUNTIME' not in env,'assembly_cache_absent_before_journey':True,'native_location_changes_identity':True},indent=2)+'\n')
# Reuse the accepted real journey verbatim except its runtime root. Its imports stay at
# the original filename, so there is no copied test helper with subtly changed behavior.
base=B/'probes/session-dogfood/check.py';raw=base.read_bytes();text=raw.decode();assert text.count("R=B.parent/'rnx'")==1
text=text.replace("R=B.parent/'rnx'","R=Path(os.environ['RNX_INSTALLED_RUNTIME'])")
(O/'driver-provenance.json').write_text(json.dumps({'source':str(base.relative_to(B)),'source_sha256':hashlib.sha256(raw).hexdigest(),'replacement':"R=B.parent/'rnx' -> R=Path(os.environ['RNX_INSTALLED_RUNTIME'])",'effective_sha256':hashlib.sha256(text.encode()).hexdigest()},indent=2)+'\n')
# The driver resolves H from this original file location; W/O are explicit inputs.
script=W/'run-dogfood.py';script.write_text('import os\nfrom pathlib import Path\np=Path('+repr(str(base))+')\ns=p.read_text().replace("R=B.parent/\'rnx\'", "R=Path(os.environ[\'RNX_INSTALLED_RUNTIME\'])")\nexec(compile(s,str(p),"exec"),{"__file__":str(p),"__name__":"__main__"})\n')
e=dict(env,RNX_DOGFOOD_TARGET=str(W),RNX_DOGFOOD_RESULTS=str(O))
with (O/'journey.log').open('w') as log:
 p=sp.run([sys.executable,str(script)],env=e,stdout=log,stderr=sp.STDOUT)
assert p.returncode==0,(O/'journey.log').read_text()
sp.run([sys.executable,str(H/'inspect.py')],check=True)
