"""Ownership and worker evidence with a runner-only consumer that owns a native presenter:
reset keeps the registry, retirement drops it exactly once (session quit and worker shutdown),
the worker presents and falls back with bounded text, settings evaluation never sees it,
and a lifecycle builder composes with presentation."""
from common import *
import importlib.util, os, re, secrets, threading, time
spec = importlib.util.spec_from_file_location('terminal_fixture', B / 'probes/project-interactive/common.py')
terminal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terminal)
cand = T / 'candidate'
work = T / 'ownership'
work.mkdir(exist_ok=True)
consumer = work / 'consumer'
(consumer / 'src').mkdir(parents=True, exist_ok=True)
(consumer / 'Cargo.toml').write_text(
    '[package]\nname="presenting-consumer"\nversion="0.0.0"\nedition="2024"\n[workspace]\n[dependencies]\n'
    f'rnx={{path={json.dumps(str(cand))},default-features=false,features=["count-allocations"]}}\n')
(consumer / 'src/main.rs').write_text(r'''
use rnx::rune;
use std::sync::Arc;
#[derive(rune::Any)]
#[rune(item = ::frame)]
struct Frame { rows: i64 }
#[derive(rune::Any)]
#[rune(item = ::frame)]
struct Broken;
#[derive(rune::Any)]
#[rune(item = ::frame)]
struct Loud;
#[derive(rune::Any)]
#[rune(item = ::scoped)]
struct Scoped(i64);
fn event(what: &str) {
    if let Some(path) = std::env::var_os("RNX_PROBE_EVENTS") {
        use std::io::Write;
        let mut f = std::fs::OpenOptions::new().create(true).append(true).open(path).unwrap();
        writeln!(f, "{what}").unwrap();
    }
}
struct Sentinel;
impl Drop for Sentinel { fn drop(&mut self) { event("presenter dropped"); } }
fn build(m: &mut rune::Module) -> Result<Vec<(String, &'static str)>, String> {
    m.ty::<Frame>().map_err(|e| e.to_string())?;
    m.ty::<Broken>().map_err(|e| e.to_string())?;
    m.ty::<Loud>().map_err(|e| e.to_string())?;
    m.function("new", |rows: i64| Frame { rows }).build_associated::<Frame>().map_err(|e| e.to_string())?;
    m.function("broken", || Broken).build().map_err(|e| e.to_string())?;
    m.function("loud", || Loud).build().map_err(|e| e.to_string())?;
    Ok(vec![("frame::Frame::new".into(), "new(rows)"), ("frame::broken".into(), "broken()"), ("frame::loud".into(), "loud()")])
}
fn present(p: &mut rnx::Presenters) -> Result<(), String> {
    event("presenter registered");
    let sentinel = Arc::new(Sentinel);
    let keep = sentinel.clone();
    p.register::<Frame>(move |f, out| { let _k = &keep; event("presented"); out.push(&format!("Frame with {} rows\n", f.rows)); Ok(()) })?;
    let keep = sentinel.clone();
    p.register::<Broken>(move |_, _| { let _k = &keep; Err("\u{1b}".repeat(100_000)) })?;
    p.register::<Loud>(move |_, out| { let _k = &sentinel; let esc = "\u{1b}".repeat(10_000); out.push(&esc); Ok(()) })
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    rnx::main_with(
        rnx::Extensions::none()
            .with("frame", build)
            .present("frame", present)
            .with_lifecycle("scoped", |m, _scope| {
                m.ty::<Scoped>().map_err(|e| e.to_string())?;
                m.function("make", |n: i64| Scoped(n)).build().map_err(|e| e.to_string())?;
                Ok(vec![("scoped::make".into(), "make(n)")])
            })
            .present("scoped", |p| p.register::<Scoped>(|s, out| { out.push(&format!("scoped {}\n", s.0)); Ok(()) })),
    )
}
''')
run(['cargo', 'build', '--offline', '--release', '--manifest-path', consumer / 'Cargo.toml', '--target-dir', work / 'build'], timeout=1800)
exe = work / 'build/release/presenting-consumer'
results = {}


def events(path):
    return path.read_text().splitlines() if path.exists() else []


def body(out):
    return '\n'.join(x for x in out.splitlines() if x.strip() and not re.match(r'\[\d+\] > ', x))


# 1. Session: reset keeps, quit drops once; bounded escaping in the emitted bytes.
ev = work / 'session-events'
ev.unlink(missing_ok=True)
env = dict(ENV, RNX_PROBE_EVENTS=str(ev), RNX_HISTORY=str(work / 'history'), RNX_CONFIG=str(work / 'absent'), TERM='xterm-256color')
t = terminal.Terminal([exe, '--no-splash'], cwd=work, env=env)
t.read()
assert events(ev) == ['presenter registered'], events(ev)
steps = {}
out = body(t.send('frame::Frame::new(3)'))
assert 'Frame with 3 rows' in out, out
out = body(t.send('scoped::make(5)'))
assert 'scoped 5' in out, out
raw = t.send('frame::loud()')
loud = t.log[-len(raw.encode()) - 4096:]
assert b'\x1b[' in t.log  # the terminal's own styling exists
assert '\\u{1b}' in raw and '\x1b\x1b' not in raw
assert raw.count('\\u{1b}') < 3000, raw.count('\\u{1b}')
steps['loud_bytes'] = len(raw.encode())
assert len(raw.encode()) < 20 * 1024, len(raw.encode())
raw = t.send('frame::broken()')
assert '<::frame::Broken> (preview unavailable: \\u{1b}' in raw, raw[:200]
steps['broken_bytes'] = len(raw.encode())
assert len(raw.encode()) < 20 * 1024
out = body(t.send('frame::Frame::new(4)'))
assert 'Frame with 4 rows' in out
before = events(ev)
os.write(t.master, b':reset\n'); t.read()
out = body(t.send('frame::Frame::new(6)'))
assert 'Frame with 6 rows' in out
assert 'presenter dropped' not in events(ev) and events(ev).count('presenter registered') == 1
os.write(t.master, b':q\n'); t.read(False)
assert t.p.wait(timeout=5) == 0
t.close()
after = events(ev)
assert after.count('presenter dropped') == 1 and after.index('presenter dropped') == len(after) - 1, after
steps['session_events'] = after
results['session'] = steps

# 2. Worker: present, fallback, bounded text, reset keeps, shutdown drops.
ev = work / 'worker-events'
ev.unlink(missing_ok=True)
cr, pw = os.pipe(); pr, cw = os.pipe()
p = subprocess.Popen([exe, 'worker', '--control-read', str(cr), '--control-write', str(cw)], pass_fds=[cr, cw],
                     stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                     env=dict(ENV, RNX_PROBE_EVENTS=str(ev)), cwd=work)
os.close(cr); os.close(cw)
send = os.fdopen(pw, 'wb', buffering=0); control = os.fdopen(pr, 'rb', buffering=0)
def reply():
    line = control.readline(4 * 1024 * 1024)
    if not line:
        rc = p.wait(timeout=10)
        raise SystemExit(f'worker closed control (exit {rc}): {p.stderr.read()[:2000]!r}')
    return json.loads(line)
assert reply()['type'] == 'ready'
assert events(ev) == ['presenter registered']
cells = {}
n = 0
def cell(op, source=None):
    global n
    n += 1
    msg = {'op': op, 'id': n, 'nonce': secrets.token_hex(32)}
    if source is not None:
        msg['source'] = source
    send.write(json.dumps(msg).encode() + b'\n')
    while True:
        r = reply()
        if r['type'] == 'settled':
            # The protocol requires an acknowledgement before another operation.
            send.write(json.dumps({'op': 'ack', 'id': n}).encode() + b'\n')
            return r
for name, src in [('frame', 'frame::Frame::new(3)'), ('broken', 'frame::broken()'), ('loud', 'frame::loud()'), ('scoped', 'scoped::make(9)'), ('plain', '42'), ('unit', 'let x = frame::Frame::new(1);')]:
    r = cell('execute', src)
    cells[name] = {'text_plain': (r['text_plain'] or '')[:120], 'bytes': len((r['text_plain'] or '').encode()), 'failure': r['failure'], 'render_bounded': r.get('render_bounded')}
assert cells['frame']['text_plain'] == 'Frame with 3 rows\n'
assert cells['scoped']['text_plain'] == 'scoped 9\n'
assert cells['broken']['text_plain'].startswith('<::frame::Broken> (preview unavailable: \\u{1b}') and cells['broken']['bytes'] <= 16384
assert cells['loud']['bytes'] <= 16384 and '\x1b' not in cells['loud']['text_plain']
assert cells['plain']['text_plain'] == '42' and cells['unit']['text_plain'] in (None, '') or cells['unit']['text_plain'] == ''
assert all(c['failure'] is None for c in cells.values())
cell('reset')
assert cell('execute', 'frame::Frame::new(8)')['text_plain'] == 'Frame with 8 rows\n'
assert 'presenter dropped' not in events(ev) and events(ev).count('presenter registered') == 1
cell('shutdown')
assert p.wait(timeout=10) == 0
worker_events = events(ev)
assert worker_events.count('presenter dropped') == 1 and worker_events[-1] == 'presenter dropped', worker_events
results['worker'] = {'cells': cells, 'events': worker_events}

# 3. Settings evaluation never reaches the extension or its presenter.
ev = work / 'settings-events'
ev.unlink(missing_ok=True)
settings = work / 'settings.rn'
settings.write_text('frame::Frame::new(1)\n')
env = dict(ENV, RNX_PROBE_EVENTS=str(ev), RNX_HISTORY=str(work / 'history2'), RNX_CONFIG=str(settings), TERM='xterm-256color')
t = terminal.Terminal([exe, '--no-splash'], cwd=work, env=env)
banner = t.read()
assert 'presented' not in events(ev), events(ev)
out = body(t.send('frame::Frame::new(2)'))
assert 'Frame with 2 rows' in out
os.write(t.master, b':q\n'); t.read(False); t.p.wait(timeout=5); t.close()
results['settings'] = {'banner': terminal.text(t.log[:600].encode() if isinstance(t.log, str) else t.log[:600]), 'events': events(ev)}
save('ownership.json', results)
print('reset keeps the registry; quit and worker shutdown drop it once; worker presents, falls back and stays bounded; settings see nothing', flush=True)
