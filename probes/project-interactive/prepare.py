from common import *
import shutil,json
P.mkdir(parents=True,exist_ok=True);(P/'dep').mkdir(exist_ok=True)
(P/'dep/mod.rn').write_text('pub fn value() { 42 }\n');(P/'dep/rnx.toml').write_text('format=1\n[source]\nroot="."\n')
(P/'main.rn').write_text('pub fn main(_) { fs::write_new("entry-ran", "must not execute")?; }\n')
(P/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath='+json.dumps(str(R))+'\n[native.polars]\npath='+json.dumps(str(R/'adapters/polars'))+'\npackage="rnx-polars"\nbuilder="build"\nhook="plain"\n[sources.dep]\npath="dep"\n')
cache=P/'.rnx/target';cache.mkdir(parents=True,exist_ok=True)
if not (cache/'release').exists():subprocess.run(['cp','-a','--reflink=auto',str(B/'probes/polars-cost/target/project/.rnx/target/release'),str(cache/'release')],check=True)
for op in ['lock','build']:
 with (O/(op+'.log')).open('w') as f:subprocess.run([T,op,'--manifest',P/'rnx.toml','--offline'],env=ENV,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
for name in ['rnx.toml','rnx.lock','rnx.Cargo.lock']:(O/name).write_bytes((P/name).read_bytes())
print('prepared',flush=True)
