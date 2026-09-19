"""Handover and worker restart with a presenter-bearing generated application:
the old registry survives a failed preparation, is dropped after cleanup and before
the replacement registers its own, the replacement's presenters work, and a fresh
worker process registers once and drops once. Reuses journey.py's cache when present
(warm Polars); otherwise Polars builds cold."""
from common import *
import importlib.util, os, re, select, time
spec = importlib.util.spec_from_file_location('terminal_fixture', B / 'probes/project-interactive/common.py')
terminal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terminal)
runtime = T / 'candidate'
work = T / 'handover'
work.mkdir(exist_ok=True)
cache = T / 'journey/cache'
adapter = work / 'adapters/frame'
(adapter / 'src').mkdir(parents=True, exist_ok=True)
(adapter / 'Cargo.toml').write_text(
    '[package]\nname = "rnx-frame"\nversion = "0.0.0"\nedition = "2024"\npublish = false\n[workspace]\n[dependencies]\n'
    f'rnx = {{ path = {json.dumps(str(runtime))}, default-features = false, features = ["count-allocations"] }}\n')
(adapter / 'src/lib.rs').write_text(r'''
use rnx::rune;
use std::sync::Arc;
#[derive(rune::Any)]
#[rune(item = ::frame)]
pub struct Frame { rows: i64 }
/// Every event names the process and executable so generations cannot be confused.
fn event(what: &str) {
    if let Some(path) = std::env::var_os("RNX_PROBE_EVENTS") {
        use std::io::Write;
        let exe = std::env::current_exe().map(|p| p.display().to_string()).unwrap_or_default();
        let mut f = std::fs::OpenOptions::new().create(true).append(true).open(path).unwrap();
        writeln!(f, "{}\t{exe}\t{what}", std::process::id()).unwrap();
    }
}
struct Sentinel;
impl Drop for Sentinel { fn drop(&mut self) { event("presenter dropped"); } }
pub fn build(m: &mut rune::Module) -> Result<Vec<(String, &'static str)>, String> {
    m.ty::<Frame>().map_err(|e| e.to_string())?;
    m.function("new", |rows: i64| Frame { rows }).build_associated::<Frame>().map_err(|e| e.to_string())?;
    Ok(vec![("frame::Frame::new".into(), "new(rows)")])
}
pub fn present(p: &mut rnx::Presenters) -> Result<(), String> {
    event("presenter registered");
    let sentinel = Arc::new(Sentinel);
    p.register::<Frame>(move |f, out| { let _k = &sentinel; event("presented"); out.push(&format!("Frame with {} rows\n", f.rows)); Ok(()) })
}
''')
# Path natives are fingerprinted from Git-tracked files: the adapter is its own committed repository.
if not (adapter / '.git').exists():
    run(['git', '-C', adapter, 'init', '-q'])
run(['git', '-C', adapter, 'add', '-A'])
run(['git', '-C', adapter, '-c', 'user.name=probe', '-c', 'user.email=probe@example', '-c', 'commit.gpgsign=false', 'commit', '-q', '--allow-empty', '-m', 'frame adapter'])
project = work / 'project'
project.mkdir(exist_ok=True)
(project / 'main.rn').write_text('pub fn main(_) { 42 }\n')
(project / 'rnx.toml').write_text(
    f'format = 1\n[application]\nentry = "main.rn"\n[runtime]\npath = "{runtime}"\n'
    f'[native.frame]\npath = "{adapter}"\npackage = "rnx-frame"\nbuilder = "build"\nhook = "plain"\npresentation = true\n')
ev = work / 'events'
ev.unlink(missing_ok=True)
env = dict(ENV, RNX_PROJECT_CACHE=str(cache), RNX_HISTORY=str(work / 'history'), RNX_CONFIG=str(work / 'absent-config'),
           RNX_PROBE_EVENTS=str(ev), TERM='xterm-256color')
t0 = time.time()
run([tool('candidate'), 'lock', '--manifest', project / 'rnx.toml', '--offline'], env=env, timeout=600)
run([tool('candidate'), 'build', '--manifest', project / 'rnx.toml', '--offline'], env=env, timeout=1800)
first_build = round(time.time() - t0, 1)
assert '.present("frame", native_0::present)' in json.loads(json.loads((project / 'rnx.lock').read_text())['assembly']['identity'])['main']


def events():
    return [l.split('\t') for l in ev.read_text().splitlines()] if ev.exists() else []


def body(out):
    return '\n'.join(x for x in out.splitlines() if x.strip() and not re.match(r'\[\d+\] > ', x))


def until(t, needle, timeout=30):
    out = ''
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if select.select([t.master], [], [], .1)[0]:
            b = os.read(t.master, 65536)
            t.log += b
            out += terminal.text(b)
            if needle in out:
                return out
    raise AssertionError((needle, out))


cwd = work / 'cwd'
cwd.mkdir(exist_ok=True)
(cwd / 'sales.csv').unlink(missing_ok=True)
t = terminal.Terminal([tool('candidate'), 'session', '--manifest', project / 'rnx.toml', '--no-splash'], cwd=cwd, env=env)
t.read()
pid = t.p.pid
# The management command execs the application in place: one pid throughout.
exe1 = os.readlink(f'/proc/{pid}/exe')
assert events() == [[str(pid), exe1, 'presenter registered']], events()
steps = {}
steps['present-1'] = body(t.send('frame::Frame::new(3)'))
assert 'Frame with 3 rows' in steps['present-1']
# A preparation failure leaves the old registry untouched.
steps['dep-unknown'] = body(t.send(':dep nope'))
assert 'unknown adapter nope' in steps['dep-unknown'], steps['dep-unknown']
os.write(t.master, b':dep polars\n')
notice = until(t, 'Continue? [y/N]')
os.write(t.master, b'n\n')
steps['dep-declined'] = body(t.read())
steps['present-after-failures'] = body(t.send('frame::Frame::new(4)'))
assert 'Frame with 4 rows' in steps['present-after-failures']
before = events()
assert [e[2] for e in before] == ['presenter registered', 'presented', 'presented'] and all(e[:2] == [str(pid), exe1] for e in before), before
# The real transition: consent, build, cleanup, exec.
os.write(t.master, b':dep polars\n')
notice = until(t, 'Continue? [y/N]')
assert 'bindings and declarations will be lost' in notice
os.write(t.master, b'y\n')
t1 = time.time()
out = t.read(timeout=1800)
transition = round(time.time() - t1, 1)
assert 'restart is beginning' in out and re.search(r'\[1\] > \r*$', out), out
exe2 = os.readlink(f'/proc/{pid}/exe')
assert exe2 != exe1 and t.p.poll() is None
after = events()
tail = after[len(before):]
# Preparation runs the replacement once as a startup probe in a child process (0063):
# that child registers and drops its own registry before commitment. The session's
# registry is dropped only after cleanup, and the exec'd replacement registers afterwards.
probe_pid = tail[0][0]
assert probe_pid != str(pid) and not os.path.exists(f'/proc/{probe_pid}'), tail
assert tail == [[probe_pid, exe2, 'presenter registered'], [probe_pid, exe2, 'presenter dropped'],
                [str(pid), exe1, 'presenter dropped'], [str(pid), exe2, 'presenter registered']], tail
assert [e[2] for e in after if e[0] == str(pid)].count('presenter dropped') == 1
steps['present-2'] = body(t.send('frame::Frame::new(5)'))
assert 'Frame with 5 rows' in steps['present-2']
assert events()[-1] == [str(pid), exe2, 'presented']
# The catalogue authored `presentation = true` for the added Polars declaration: a bare frame presents.
manifest = (project / 'rnx.toml').read_text()
assert 'presentation = true' in manifest.split('[native.polars]', 1)[1], manifest
steps['csv'] = body(t.send('fs::write_new("sales.csv", "item,qty\\napple,3\\npear,1\\n")?;'))
steps['polars-bare'] = body(t.send('polars::read_csv("sales.csv", [("item","string"),("qty","i64")])?'))
assert 'DataFrame: 2 rows × 2 columns' in steps['polars-bare'] and '"apple" | 3' in steps['polars-bare'], steps['polars-bare']
os.write(t.master, b':q\n')
t.read(False)
assert t.p.wait(timeout=10) == 0
final = events()
assert final[-1] == [str(pid), exe2, 'presenter dropped'] and [e[2] for e in final if e[0] == str(pid)].count('presenter dropped') == 2, final
t.close()
(work / 'session.pty').write_bytes(t.log)

# Worker restart: a fresh worker process registers once and drops once; nothing from the old one leaks.
import secrets
app = exe2
worker_events = work / 'worker-events'
worker_events.unlink(missing_ok=True)
workers = []


def worker_round(n):
    cr, pw = os.pipe(); pr, cw = os.pipe()
    p = subprocess.Popen([app, 'worker', '--control-read', str(cr), '--control-write', str(cw)], pass_fds=[cr, cw],
                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env=dict(ENV, RNX_PROBE_EVENTS=str(worker_events)), cwd=work)
    os.close(cr); os.close(cw)
    send = os.fdopen(pw, 'wb', buffering=0); control = os.fdopen(pr, 'rb', buffering=0)

    def reply():
        line = control.readline(4 * 1024 * 1024)
        assert line, p.stderr.read()
        return json.loads(line)

    def op(i, kind, source=None):
        msg = {'op': kind, 'id': i, 'nonce': secrets.token_hex(32)}
        if source is not None:
            msg['source'] = source
        send.write(json.dumps(msg).encode() + b'\n')
        while True:
            r = reply()
            if r['type'] == 'settled':
                send.write(json.dumps({'op': 'ack', 'id': i}).encode() + b'\n')
                return r
    assert reply()['type'] == 'ready'
    r = op(1, 'execute', f'frame::Frame::new({n})')
    assert r['text_plain'] == f'Frame with {n} rows\n', r
    r = op(2, 'execute', '[frame::Frame::new(1)]')
    assert r['text_plain'] == '[<::frame::Frame>]', r
    op(3, 'reset')
    r = op(4, 'execute', f'frame::Frame::new({n + 1})')
    assert r['text_plain'] == f'Frame with {n + 1} rows\n', r
    op(5, 'shutdown')
    assert p.wait(timeout=10) == 0, p.stderr.read()
    send.close(); control.close()
    return p.pid


pids = [worker_round(3), worker_round(7)]
lines = [l.split('\t') for l in worker_events.read_text().splitlines()]
assert pids[0] != pids[1]
per = {pid: [e[2] for e in lines if e[0] == str(pid)] for pid in pids}
expected = ['presenter registered', 'presented', 'presented', 'presenter dropped']
assert per == {pids[0]: expected, pids[1]: expected}, per
assert [e[0] for e in lines] == [str(pids[0])] * 4 + [str(pids[1])] * 4, lines
assert all(e[1] == app for e in lines)
save('handover.json', {
    'pid': pid, 'startup_probe_pid': int(probe_pid), 'first_executable': exe1, 'replacement_executable': exe2, 'first_build_seconds': first_build,
    'transition_seconds': transition, 'events': final, 'steps': steps, 'consent_notice': notice,
    'worker_pids': pids, 'worker_events': lines,
})
print(f'handover: startup probe child registered and dropped, then the session dropped its registry after cleanup and the exec\'d replacement registered ({transition} s); '
      f'preparation failures kept it; two worker processes each registered once and dropped once', flush=True)
