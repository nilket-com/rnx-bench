"""An old-tool scratch keeps its declared runtime when the default migrates."""
from pathlib import Path
import os,json,subprocess as sp,importlib.util,time,select,shlex,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target/real';O=B/'results/runtime-migration-0065';d=json.loads((W/'setup.json').read_text());E=json.loads((W/'env.json').read_text());E.update(RNX_PROJECT_TOOL=d['old_tool'],XDG_STATE_HOME=str(W/"old scratch ' state"),RNX_HISTORY=str(W/'old-scratch-history'))
def call(a):
 p=sp.run(list(map(str,a)),env=E,cwd=W,capture_output=True,text=True,timeout=90);assert p.returncode==0,(a,p.stdout,p.stderr);return p
call([d['old_tool'],'runtime','select',d['old_id']])
spec=importlib.util.spec_from_file_location('term',B/'probes/project-interactive/common.py');term=importlib.util.module_from_spec(spec);spec.loader.exec_module(term);t=term.Terminal([d['launcher'],'--no-splash','--color=never'],W,E)
def until(needle):
 out='';end=time.monotonic()+600
 while time.monotonic()<end:
  if select.select([t.master],[],[],.1)[0]:
   b=os.read(t.master,65536);t.log+=b;out+=term.text(b)
   if needle in out:return out
 raise AssertionError(out)
try:
 t.read();os.write(t.master,b':dep --offline polars\n');notice=until('Continue? [y/N]');assert d['old_id'] in notice;os.write(t.master,b'y\n');out=until('[1] >');assert 'restart is beginning' in out
 line=out.split('Reopen this scratch session:\r\n  ',1)[1].split('\r\n',1)[0];args=shlex.split(line);m=Path(args[3]);pair=[m.parent/'rnx.lock',m.parent/'rnx.Cargo.lock',m.parent/'.rnx/receipt.json'];before=[p.read_bytes() for p in pair];assert json.loads(before[0])['format']==2 and json.loads(before[2])['format']==3
 assert 'true' in t.send('polars::lit(1).is_ok()');os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=10)==0
 call([d['tool'],'runtime','install','--from',d['source']]);assert [p.read_bytes() for p in pair]==before
 reopened=sp.run(args,input='polars::lit(1).is_ok()\n:q\n',env=E,cwd=W,capture_output=True,text=True,timeout=30);assert reopened.returncode==0 and 'true' in reopened.stdout
 call([d['tool'],'lock','--offline','--manifest',m]);lock=json.loads((m.parent/'rnx.lock').read_text());assert lock['format']==3 and lock['declarations']['runtime']['path']==d['source']
 identity=json.loads(lock['assembly']['identity']);assert d['source'] in identity['manifest']
 (O/'old-scratch.pty').write_bytes(t.log);(O/'scratch.json').write_text(json.dumps(dict(manifest=str(m),old_source=d['source'],default_migration_left_pair_and_receipt_unchanged=True,old_tool_reopened=True,explicit_relock_kept_declared_source=True,new_lock_format=3),indent=2)+'\n');print('PASS old scratch independence and explicit relock path')
finally:t.close()
