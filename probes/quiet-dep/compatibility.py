"""The two peer directions: a new session with the older tool refuses `:dep` before anything is
written and still serves `:depv`; an older session with the new tool is prompted and verbose."""
from common import *
prep = json.loads((O / 'prepare.json').read_text())
b = prep['binaries']
rows = {}
# New session (runner-only, consults RNX_PROJECT_TOOL) + old tool (capability 1).
d, env = home('new-session-old-tool')
t = session(b['product-runner']['path'], env, d / 'work', {'RNX_PROJECT_TOOL': b['baseline']['path']})
os.write(t.master, b':dep polars\n')
out = t.read(timeout=120)
lines = body(out)
assert any('predates quiet preparation' in l and ':depv' in l for l in lines), lines
assert not list((d / 'state').glob('rnx/sessions/*')), 'nothing written before the refusal'
os.write(t.master, b':depv polars\n')
notice = until(t, 'Continue? [y/N]', timeout=120)
assert 'New scratch project' in notice
os.write(t.master, b'n\n')
t.read()
rows['new_session_old_tool'] = {'dep': lines, 'depv_prompted': True}
quit(t)
# Old session (runner-only) + new tool: no mode field; prompted, verbose.
d, env = home('old-session-new-tool')
t = session(b['baseline-runner']['path'], env, d / 'work', {'RNX_PROJECT_TOOL': b['product']['path']})
os.write(t.master, b':dep polars\n')
notice = until(t, 'Continue? [y/N]', timeout=120)
assert 'New scratch project' in notice and 'Existing bindings and declarations will be lost' in notice
os.write(t.master, b'n\n')
t.read()
rows['old_session_new_tool'] = {'prompted': True, 'notice_lines': len(body(notice))}
quit(t)
save('compatibility.json', rows)
print('compatibility: new session + old tool refuses :dep by name and serves :depv; old session + new tool is prompted and verbose', flush=True)
