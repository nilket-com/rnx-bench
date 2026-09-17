"""Replay the real 0060 PTY journey as an override, without rebuilding Polars.
The shared Polars build is gate 5; this is the override/interactive regression.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile,types
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/cache-regression-0061/commands';T=R/'tools/project/target/debug/rnx-project'
old=B/'probes/project-interactive/target/project';receipt=json.loads((old/'.rnx/receipt.json').read_text());artifact=Path(os.environ.get('RNX_POLARS_ARTIFACT',str(old/'.rnx/artifacts'/receipt['executable_sha256'])))
assert artifact.is_file(),artifact
with tempfile.TemporaryDirectory(prefix='rnx-cache-override-pty-') as tmp:
 p=Path(tmp);sha=hashlib.sha256(artifact.read_bytes()).hexdigest();dest=p/'.rnx/artifacts'/sha;dest.parent.mkdir(parents=True);shutil.copy2(artifact,dest)
 (p/'main.rn').write_text('pub fn main(_){fs::write_new("entry-ran", "wrong").unwrap();}\n');(p/'dep').mkdir();(p/'dep/rnx.toml').write_text('format=1\n[source]\nroot="."\n');(p/'dep/mod.rn').write_text('pub fn value(){42}\n')
 (p/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[executable]\npath='+json.dumps(str(dest))+'\n[sources.dep]\npath="dep"\n')
 common=types.ModuleType('common');common.__file__=str(B/'probes/project-interactive/common.py');exec(Path(common.__file__).read_text(),common.__dict__);common.P=p;common.T=T;common.O=O
 env=dict(common.ENV,RNX_CONFIG=str(p/'absent'));subprocess.run([T,'lock','--manifest',p/'rnx.toml'],env=env,check=True,capture_output=True);subprocess.run([T,'eval','--manifest',p/'rnx.toml','--','42'],env=env,check=True,capture_output=True)
 common.ENV=env;sys.modules['common']=common
 journey=B/'probes/project-interactive/journey.py';exec(compile(journey.read_text(),str(journey),'exec'),{'__name__':'__main__','__file__':str(journey)})
 (O/'polars-override.json').write_text(json.dumps({'artifact_sha256':sha,'source_fixture_sha256':hashlib.sha256(journey.read_bytes()).hexdigest(),'common_sha256':hashlib.sha256(Path(common.__file__).read_bytes()).hexdigest(),'scope':'unchanged 0060 journey, injected private override project; actual shared Polars build deferred to gate 5'},indent=2)+'\n')
