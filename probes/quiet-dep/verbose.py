"""`:depv` held to 0067's journey: a declined request keeps bindings and writes nothing; the accepted
one shows the notice with the revision, prints "restart is beginning", the replacement prints the
reopen command, bindings are lost, history keeps the typed line, a second request is a no-op with
its message, and a combined offline request names what is added and what is declared."""
from common import *
prep = json.loads((O / 'prepare.json').read_text())
rnx = prep['binaries']['product']['path']
rev = prep['revs']['product']['fixture']
rows = {}
d, env = home('verbose')
cwd = d / 'work'
t = session(rnx, env, cwd, splash=True)
t.send('let held = 42;')
os.write(t.master, b':depv polars\n')
notice = until(t, 'Continue? [y/N]', timeout=120)
assert rev in notice and 'Adding: polars' in notice and 'Existing bindings and declarations will be lost' in notice, notice
os.write(t.master, b'n\n')
t.read()
assert not (d / 'state').exists() and not (d / 'cache').exists(), 'a declined request writes nothing'
assert '42' in t.send('held')
t.send('let history_marker = 93817;')
os.write(t.master, b':depv polars\n')
notice = until(t, 'Continue? [y/N]', timeout=120)
os.write(t.master, b'y\n')
out = t.read(timeout=1800)
assert 'restart is beginning' in out and 'Reopen this scratch session:' in out and 'dependency phase: startup check' in out, out[-1500:]
assert re.search(r'\[1\] > \r*$', out)
assert 'No local variable' in t.send('held')
history = Path(env['RNX_HISTORY']).read_text()
assert ':depv polars' in history and 'history_marker = 93817' in history
assert 'No local variable' in t.send('history_marker')
assert 'already installed; session unchanged' in t.send(':depv polars')
scratch = sorted((d / 'state/rnx/sessions').glob('session-*'))[-1]
assert not (scratch / '.rnx/dep.log').exists(), 'verbose writes no log'
t.send('let held = 42;')
os.write(t.master, b':depv --offline polars postgres\n')
notice2 = until(t, 'Continue? [y/N]', timeout=120)
assert 'Adding: postgres' in notice2 and 'Already declared: polars' in notice2 and 'Offline' in notice2, notice2
os.write(t.master, b'y\n')
out2 = t.read(timeout=1800)
assert 'restart is beginning' in out2 and 'Reopen this scratch session:' not in out2 and 'No local variable' in t.send('held')
assert 'Missing item' not in t.send('postgres::query')
quit(t)
rows.update({'declined_kept_bindings_and_wrote_nothing': True, 'notice_first_lines': notice.replace('\r', '').split('\n')[1:4], 'restart_announced': True,
             'reopen_printed_by_replacement': True, 'history_keeps_typed_line': True, 'no_op_message': 'already installed; session unchanged',
             'combined_offline_notice': [l for l in notice2.replace('\r', '').split('\n') if l.startswith(('Adding', 'Already', 'Offline'))]})
save('verbose.json', rows)
print('verbose: 0067\'s journey holds under :depv — decline, notice, restart announcement, reopen from the replacement, bindings lost, history, no-op message, combined offline', flush=True)
