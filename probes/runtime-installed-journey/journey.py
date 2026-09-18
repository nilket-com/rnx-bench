"""Full product journeys from installed source, original checkout physically renamed."""
from pathlib import Path
import os,sys,json,subprocess as sp,hashlib,shutil,importlib.util,select,time
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/runtime-installed-journey-0064';C=W/'original';T=W/'bin/rnx-project';S=W/'bin/rnx'
assert C.is_dir() and not (W/'unavailable-original').exists()
E={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','GIT_','CARGO_','RUST'))}
E.update(TERM='xterm-256color',POLARS_MAX_THREADS='1',PYTHONDONTWRITEBYTECODE='1',RNX_PROJECT_TOOL=str(T),RNX_PROJECT_CACHE=str(W/'cache'),RNX_CONFIG=str(W/'absent-settings'),XDG_STATE_HOME=str(W/"state ' private"),XDG_DATA_HOME=str(W/'data'),RNX_HISTORY=str(W/'override-history'))
def call(a,e=E):
 p=sp.run(list(map(str,a)),env=e,cwd=W,capture_output=True,text=True,timeout=180);assert p.returncode==0,(a,p.stdout,p.stderr);return p.stdout
out=call([T,'runtime','install','--from',C]);id=out.split('runtime ',1)[1].splitlines()[0];entry=W/'data/rnx/runtimes/entries'/id;I=entry/'source';doc=json.loads((entry/'installation.json').read_text());assert not doc['dirty_tracked'];assert doc['source_commit']==json.loads((O/'snapshot-build.json').read_text())['fixture_commit'];assert doc['tool_sha256']==hashlib.sha256(T.read_bytes()).hexdigest()
names=sp.check_output(['git','-C',str(C),'ls-files','-z']).decode().split('\0');names=[n for n in names if n];other=sp.check_output(['git','-C',str(I),'ls-files','-z']).decode().split('\0');assert names==[n for n in other if n]
for n in names:assert (C/n).read_bytes()==(I/n).read_bytes() and bool((C/n).stat().st_mode&0o111)==bool((I/n).stat().st_mode&0o111),n
# Equal source snapshot, unequal identity from different canonical native paths.
keys={}
for name,runtime in [('checkout',C),('installed',I)]:
 p=W/('identity-'+name);p.mkdir();(p/'entry.rn').write_text('pub fn main(_) { 42 }\n');m=p/'rnx.toml';m.write_text('format=1\n[application]\nentry="entry.rn"\n[runtime]\npath='+json.dumps(str(runtime))+'\n')
 e=dict(E,RNX_PROJECT_CACHE=str(W/'identity-cache'))
 call([T,'add','polars','postgres','--manifest',m],e);call([T,'lock','--offline','--manifest',m],e)
 lock=json.loads((p/'rnx.lock').read_text());keys[name]=lock['assembly'];(O/(name+'-lock.json')).write_text(json.dumps(lock,indent=2)+'\n')
assert keys['checkout']!=keys['installed'];C.rename(W/'unavailable-original');assert not C.exists() and not (W/'cache').exists()
for rel in ['objects/info/alternates','commondir','gitdir']:assert not (I/'.git'/rel).exists()
assert 'worktree' not in (I/'.git/config').read_text().lower()
(O/'installation.json').write_text(json.dumps(doc,indent=2)+'\n')
(O/'snapshot.json').write_text(json.dumps(dict(original=str(C),installed=str(I),files=len(names),equal_source_bytes_and_modes=True,tree_sha256=doc['tree_sha256'],location_changes_key=True,original_absent=True,cold_cache=True,launcher_sha256=hashlib.sha256(S.read_bytes()).hexdigest(),tool_sha256=hashlib.sha256(T.read_bytes()).hexdigest()),indent=2)+'\n')
# Explicit override notice before consent, using same installed root and no mutation.
spec=importlib.util.spec_from_file_location('term',B/'probes/project-interactive/common.py');term=importlib.util.module_from_spec(spec);spec.loader.exec_module(term)
t=term.Terminal([S,'--no-splash','--color=never'],W,dict(E,RNX_DEP_RUNTIME=str(I)))
try:
 t.read();os.write(t.master,b':dep --offline polars\n');text='';end=time.monotonic()+30
 while 'Continue? [y/N]' not in text:
  assert time.monotonic()<end
  if select.select([t.master],[],[],.1)[0]:
   b=os.read(t.master,65536);t.log+=b;text+=term.text(b)
 assert 'Runtime: override '+str(I) in text;os.write(t.master,b'n\n');t.read();os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=10)==0
 (O/'override.pty').write_bytes(t.log)
finally:t.close()
assert not Path(E['XDG_STATE_HOME']).exists() and not (W/'cache').exists()
(W/'env.json').write_text(json.dumps(E,indent=2)+'\n')
base=B/'probes/session-dogfood/check.py';raw=base.read_text();assert raw.count("R=B.parent/'rnx'")==1
text=raw.replace("R=B.parent/'rnx'",'R=Path('+repr(str(I))+')')
needle="assert 'bindings and declarations will be lost' in notice"
assert text.count(needle)==1
text=text.replace(needle,needle+'\n if "New scratch project:" in notice:\n  assert '+repr('Runtime: installation '+id+' at '+str(I))+' in notice\n  assert '+repr(str(C))+' in notice and '+repr(doc['source_commit'])+' in notice')
(O/'effective-dogfood.py').write_text(text)
(O/'driver-provenance.json').write_text(json.dumps(dict(original='probes/session-dogfood/check.py',original_sha256=hashlib.sha256(raw.encode()).hexdigest(),effective_sha256=hashlib.sha256(text.encode()).hexdigest(),changes='only installed R path plus default-runtime/provenance notice assertions'),indent=2)+'\n')
script=W/'run.py';script.write_text('from pathlib import Path\np=Path('+repr(str(base))+')\ns=Path('+repr(str(O/'effective-dogfood.py'))+').read_text()\nexec(compile(s,str(p),"exec"),{"__file__":str(p),"__name__":"__main__"})\n')
with (O/'journey.log').open('w') as log:
 p=sp.run([sys.executable,str(script)],env=dict(E,RNX_DOGFOOD_TARGET=str(W),RNX_DOGFOOD_RESULTS=str(O)),stdout=log,stderr=sp.STDOUT)
assert p.returncode==0,(O/'journey.log').read_text()
# No consumer inventory or generated assembly is routed through the unavailable path.
checked=[]
for pattern in ['cache/entries/*/assembly/Cargo.toml',"state ' private/rnx/sessions/*/rnx.lock","state ' private/rnx/sessions/*/rnx.Cargo.lock",'absolute-project/rnx.lock','relative-project/rnx.lock']:
 for path in W.glob(pattern):
  assert str(C).encode() not in path.read_bytes(),path;checked.append(str(path.relative_to(W)))
assert len(checked)>=6
(O/'unavailable-path-check.json').write_text(json.dumps(dict(original_absent=not C.exists(),checked=checked),indent=2)+'\n')
print('PASS gate 4 installed full product journeys',flush=True)
