"""Build an old consumer from a genuine retained runtime with checkout absent."""
from pathlib import Path
import os,subprocess as sp,json,shutil,tarfile,io,time,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target/real';O=Path(os.environ.get('RNX_REMOVAL_RESULTS',str(B/'results/removal-storage-0066'))).resolve();O.mkdir(parents=True,exist_ok=True);assert not W.exists();W.mkdir(parents=True);C=W/'original';C.mkdir()
with tarfile.open(fileobj=io.BytesIO(sp.check_output(['git','-C',R,'archive','7cd3205']))) as f:f.extractall(C,filter='data')
E={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','GIT_','CARGO_','RUST'))};E.update(XDG_DATA_HOME=str(W/"data ' private"),XDG_STATE_HOME=str(W/'state'),RNX_PROJECT_CACHE=str(W/'cache'),RNX_CONFIG=str(W/'absent'),RNX_HISTORY=str(W/'history'),TERM='xterm-256color',POLARS_MAX_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
for args in [['init','-q'],['add','.'],['-c','user.name=Fixture','-c','user.email=f@invalid','-c','commit.gpgsign=false','commit','-qm','snapshot']]:sp.run(['git','-C',C,*args],env=E,check=True)
(W/'bin').mkdir();T=W/'bin/rnx-project';S=W/'bin/rnx';shutil.copy2(B/'probes/removal-commands/target/bin/rnx-project-ordinary',T);shutil.copy2(B/'probes/removal-commands/target/bin/rnx-project-support',W/'bin/rnx-project-support');shutil.copy2(Path(os.environ.get('RNX_REMOVAL_LAUNCHER',str(R/'target/release/rnx'))),S);E['RNX_PROJECT_TOOL']=str(T)
OLD=Path(os.environ.get('RNX_REMOVAL_OLD_TOOL',str(B/'probes/native-inventory/target/stock/tools/project/target/release/rnx-project')))
def call(a):
 p=sp.run(list(map(str,a)),env=E,cwd=W,capture_output=True,text=True,timeout=1200);assert p.returncode==0,(a,p.stdout,p.stderr);return p
r=call([OLD,'runtime','install','--from',C]);id=r.stdout.split('runtime ',1)[1].splitlines()[0];store=Path(E['XDG_DATA_HOME'])/'rnx/runtimes';entry=store/'entries'/id;source=entry/'source';C.rename(W/'unavailable-original');assert not C.exists() and not (W/'cache').exists()
# An independently packaged fixture extension observes retained OUT_DIR ownership.
n=W/'keep';(n/'src').mkdir(parents=True);(n/'Cargo.toml').write_text('[package]\nname="keep-adapter"\nversion="0.0.0"\nedition="2024"\n[workspace]\n[dependencies]\nrnx={path='+json.dumps(str(source))+'}\n')
(n/'build.rs').write_text('fn main(){std::fs::write(format!("{}/retained.txt",std::env::var("OUT_DIR").unwrap()),"before").unwrap();}')
(n/'src/lib.rs').write_text('pub fn build(m:&mut rnx::rune::Module)->Result<Vec<(String,&\'static str)>,String>{m.function("read",||std::fs::read_to_string(concat!(env!("OUT_DIR"),"/retained.txt")).unwrap()).build().map_err(|e|e.to_string())?;Ok(vec![])}')
sp.run(['git','init','-q',n],check=True,env=E);sp.run(['git','-C',n,'add','.'],check=True,env=E)
a=W/'old-project';a.mkdir();m=a/'rnx.toml';(a/'entry.rn').write_text('pub fn main(_) { keep::read() }\n');m.write_text('format=1\n[application]\nentry="entry.rn"\n[runtime]\npath='+json.dumps(str(source))+'\n[native.keep]\npath="../keep"\npackage="keep-adapter"\nbuilder="build"\nhook="plain"\n')
call([OLD,'add','polars','--manifest',m]);call([OLD,'lock','--offline','--manifest',m]);t=time.monotonic();r=call([OLD,'build','--offline','--manifest',m]);(O/'old-build.log').write_text(r.stdout+r.stderr)
rec=json.loads((a/'.rnx/receipt.json').read_text());artifact=W/'cache/entries'/rec['assembly_key']/'artifacts'/rec['executable_sha256'];retained=list((artifact.parent.parent/'target').rglob('retained.txt'));assert len(retained)==1
for p in [a/'rnx.lock',a/'rnx.Cargo.lock',artifact.parent.parent/'assembly/Cargo.toml']:assert str(C).encode() not in p.read_bytes()
(W/'env.json').write_text(json.dumps(E));(W/'setup.json').write_text(json.dumps(dict(old_tool=str(OLD),tool=str(T),launcher=str(S),store=str(store),old_id=id,source=str(source),artifact=str(artifact),retained=str(retained[0]),old_manifest=str(m)),indent=2))
(O/'old-setup.json').write_text(json.dumps(dict(original_absent=True,cold_cache=True,old_id=id,old_artifact=str(artifact),retained=str(retained[0]),build_seconds=time.monotonic()-t,old_tool_sha256=hashlib.sha256(OLD.read_bytes()).hexdigest(),current_tool_sha256=hashlib.sha256(T.read_bytes()).hexdigest()),indent=2)+'\n');print('PASS old installed assembly with original checkout absent',flush=True)
