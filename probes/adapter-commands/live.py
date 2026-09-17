"""An add is an authoring operation; an existing session keeps its bindings."""
from common import *
import importlib.util,shutil,tempfile
spec=importlib.util.spec_from_file_location('terminal_fixture',B/'probes/project-interactive/common.py');terminal=importlib.util.module_from_spec(spec);spec.loader.exec_module(terminal)
app=W/'live';app.mkdir();shutil.copyfile(APPS[1]/'rnx.toml',app/'rnx.toml');(app/'main.rn').write_text('pub fn main(_) { 42 }\n')
logged('live-lock',command('lock',app,['--offline']));logged('live-attach',command('build',app,['--offline']))
assert artifact(app)==artifact()
with tempfile.TemporaryDirectory(prefix='rnx-add-live-') as d:
 t=terminal.Terminal(command('session',app,['--no-splash','--color=never']),Path(d),ENV)
 try:
  t.read();t.send('let retained = 42;');logged('live-add-postgres',command('add',app,['postgres']))
  assert '42' in t.send('retained')
  assert 'true' in t.send('polars::lit(1).is_ok()')
  out=t.send('postgres::query("", "", [], #{})');assert 'Missing item' in out or 'missing item' in out.lower(),out
  os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=5)==0
 finally:
  (O/'live-pty.bin').write_bytes(t.log);(O/'live-pty.txt').write_text('\n'.join(line.rstrip() for line in terminal.text(t.log).splitlines())+'\n');t.close()
save('live.json',{'binding_retained_after_add':True,'polars_still_usable':True,'new_adapter_not_loaded_into_running_session':True})
print('PASS running session unchanged by add',flush=True)
