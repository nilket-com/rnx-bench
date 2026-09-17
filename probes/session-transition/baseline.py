"""Ordinary entry behavior remains byte-identical in the isolated root copy."""
from pathlib import Path
import json,os,subprocess,tempfile
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/session-transition-0063';A=H/'target/root/target/debug/rnx';OLD=R/'target/release/rnx'
env={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','CARGO_','RUST'))};cases=[]
with tempfile.TemporaryDirectory(prefix='rnx-dep-baseline-') as d:
 w=Path(d);env.update(RNX_CONFIG=str(w/'absent'),RNX_HISTORY=str(w/'history'));f=w/'main.rn';f.write_text('pub fn main(_) { println!("file value"); }\n')
 for args in [['version'],['--color=never','eval','42'],['--color=never','eval',''],['--color=never','eval'],['run'],['run',str(f)],['--color=never','repl']]:
  outputs=[]
  for exe in [OLD,A]:
   p=subprocess.run([exe,*args],input='let n=42;\nn\n:q\n',env=env,capture_output=True,text=True,timeout=10);outputs.append((p.returncode,p.stdout,p.stderr))
  assert outputs[0]==outputs[1],(args,outputs);cases.append({'args':args,'status_stdout_stderr_equal':True})
(O/'ordinary-entry.json').write_text(json.dumps(cases,indent=2)+'\n');print('PASS seven ordinary entry comparisons')
