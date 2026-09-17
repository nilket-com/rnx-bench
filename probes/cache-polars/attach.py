"""Full ready-hit validation/receipt publication is a separate measured cost."""
from common import *
import statistics

cpu = min(os.sched_getaffinity(0))
os.sched_setaffinity(0,{cpu})
trap_log = W / 'compiler-trap.log'
assert not trap_log.exists()
trapped = dict(ENV,PATH=str(W/'traps')+':'+ENV['PATH'])
rows = []
a = artifact()
ready = a.parent.parent/'ready.json'
before = (sha(ready),sha(a),a.stat().st_ino,a.stat().st_mtime_ns)
for n in range(5):
    for app in (APPS if n%2==0 else list(reversed(APPS))):
        ms = logged(f'attach-{app.name}-{n}',command('build',app,['--offline']),trapped)
        assert 'attached shared' in (O/f'attach-{app.name}-{n}.log').read_text()
        assert artifact(app)==a and not trap_log.exists()
        rows.append({'project':app.name,'sample':n,'ms':ms})
assert before == (sha(ready),sha(a),a.stat().st_ino,a.stat().st_mtime_ns)
save('attachments.json',{'cpu':cpu,'samples':rows,'median_ms':statistics.median(x['ms'] for x in rows),
    'includes':'input/context validation, allowed tool-version observations, full executable hash against ready digest, project receipt publication',
    'compilation_trapped':True,'ready_and_artifact_unchanged':True})
print('PASS ten full-validation attachments, median ms',statistics.median(x['ms'] for x in rows),flush=True)
