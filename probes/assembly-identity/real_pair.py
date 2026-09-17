"""Real Polars declaration control; lock only, no duplicate heavy builds."""
from pathlib import Path
import hashlib,json,os,subprocess,tempfile,shutil
B=Path(__file__).resolve().parents[2];R=B.parent/'rnx';O=B/'results/assembly-identity-0061';T=R/'tools/project/target/release/rnx-project'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_'))};rows=[]
with tempfile.TemporaryDirectory(prefix='rnx-real-assembly-key-') as tmp:
 root=Path(tmp)
 for name,value in [('real-polars-a',42),('real-polars-b',99)]:
  p=root/name;p.mkdir();(p/'main.rn').write_text(f'pub fn main(_) {{ {value} }}\n')
  (p/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath='+json.dumps(str(R))+'\n[native.polars]\npath='+json.dumps(str(R/'adapters/polars'))+'\npackage="rnx-polars"\nbuilder="build"\nhook="plain"\n')
  result=subprocess.run([T,'lock','--manifest',p/'rnx.toml','--offline'],env=ENV,capture_output=True,text=True,timeout=120);d=O/name;d.mkdir(exist_ok=True);(d/'lock.log').write_text(result.stdout+result.stderr);assert result.returncode==0,result.stderr
  for src,dst in [(p/'rnx.toml','rnx.toml'),(p/'rnx.lock','rnx.lock'),(p/'rnx.Cargo.lock','rnx.Cargo.lock'),(p/'.rnx/assembly/Cargo.toml','Cargo.toml'),(p/'.rnx/assembly/src/main.rs','main.rs')]:shutil.copyfile(src,d/dst)
  rows.append({f:hashlib.sha256((d/f).read_bytes()).hexdigest() for f in ['rnx.lock','rnx.Cargo.lock','Cargo.toml','main.rs']})
 assert rows[0]['rnx.lock']!=rows[1]['rnx.lock']
 for name in ['rnx.Cargo.lock','Cargo.toml','main.rs']:assert rows[0][name]==rows[1][name]
(O/'real-pair.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS: real Polars projects have different project locks and identical generated manifest, main and Cargo lock')
