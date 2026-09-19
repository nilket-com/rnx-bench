"""Build a real project using tiny catalogue-shaped adapters (no Polars engine)."""
from pathlib import Path
import json,os,subprocess,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=Path('/home/me/work/rnx-bench/probes/removal-final/target/preparation');T=R/'tools/project/target/debug/rnx-project'
W.mkdir(exist_ok=True)
shutil.copy2(R/'target/debug/rnx',W/'stock-rnx')
env={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','CARGO_','RUST'))}
env.update(XDG_DATA_HOME=str(W/'data'),PYTHONDONTWRITEBYTECODE='1',RNX_PROJECT_CACHE=str(W/'cache'),RNX_PROJECT_TOOL=str(T),RNX_CONFIG=str(W/'absent-config'),RNX_HISTORY=str(W/'history'),TERM='xterm-256color',XDG_STATE_HOME=str(W/'state'))
def run(args,**kw):return subprocess.run(list(map(str,args)),env=env,check=True,**kw)
n=W/'native';n.mkdir(exist_ok=True)
(n/'src').mkdir(exist_ok=True)
(n/'Cargo.toml').write_text(f'''[package]
name="rnx"
version="0.0.1"
edition="2024"
[workspace]
[features]
project-sources=["actual/project-sources"]
[dependencies]
actual={{package="rnx",path={json.dumps(str(R))}}}
''')
(n/'src/lib.rs').write_text('pub use actual::*;\n')
for name in ['polars','postgres','fixture']:
 d=n/'adapters'/name;(d/'src').mkdir(parents=True,exist_ok=True)
 (d/'Cargo.toml').write_text(f'[package]\nname="rnx-{name}"\nversion="0.0.0"\nedition="2024"\n[workspace]\n[dependencies]\nrnx={{path="../.."}}\n')
 if name=='fixture':(d/'src/lib.rs').write_bytes((H/'fixture.rs').read_bytes())
 elif name=='polars':(d/'src/lib.rs').write_text('pub fn build(_: &mut rnx::rune::Module) -> Result<Vec<(String, &\'static str)>,String> { Ok(vec![]) }\n')
 else:(d/'src/lib.rs').write_text('pub fn build(_: &mut rnx::rune::Module, _:rnx::Scope) -> Result<Vec<(String, &\'static str)>,String> { Ok(vec![]) }\n')
run(['git','init','-q',n]);run(['git','-C',n,'add','.'])
p=W/'project';p.mkdir(exist_ok=True)
(p/'main.rn').write_text('pub fn main(_) { 42 }\n')
(p/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath="../native"\n[native.fixture]\npath="../native/adapters/fixture"\npackage="rnx-fixture"\nbuilder="build"\nhook="lifecycle"\n')
run([T,'lock','--offline','--manifest',p/'rnx.toml'])
run([T,'build','--offline','--manifest',p/'rnx.toml'])
(W/'env.json').write_text(json.dumps(env,indent=2))
print('real project ready',flush=True)
