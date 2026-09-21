"""The two spellings at a real prompt with the stock product: `:dep polars` quiet (first build, then an
attach in a fresh session, then `:dep postgres`), `:depv` verbose, a quiet failure's tail, Ctrl-C during a
quiet build, and the same key with and without capture."""
from common import *
prep = json.loads((O / 'prepare.json').read_text())
rnx = prep['binaries']['product']['path']
rows = {}


def dep(t, line, quiet, timeout=1800):
    """Send a :dep/:depv line; answer the prompt in verbose mode; return the lines between the echo and the next prompt."""
    os.write(t.master, (line + '\n').encode())
    if not quiet:
        notice = until(t, 'Continue? [y/N]')
        os.write(t.master, b'y\n')
    else:
        notice = ''
    out = t.read(timeout=timeout)
    return notice, out


def silent(out, echo):
    """Quiet success: nothing between the echo and the replacement's first prompt."""
    lines = body(out)
    assert lines and lines[0].strip() == echo, lines
    assert lines[1:] == [], lines[1:]
    assert re.search(r'\[1\] > \r*$', out), out[-200:]
    return lines


d, env = home('quiet')
cwd = d / 'work'
t = session(rnx, env, cwd, splash=True)  # a session with a banner: the replacement must not print one
t0 = time.monotonic()
_, out = dep(t, ':dep polars', True)
first_s = round(time.monotonic() - t0, 1)
lines = silent(out, ':dep polars')
scratch = [p for p in (d / 'state/rnx/sessions').glob('session-*/rnx.toml')]
assert len(scratch) == 1
log = scratch[0].parent / '.rnx/dep.log'
text = log.read_text(errors='replace')
assert log.exists() and 'Compiling' in text and (log.stat().st_mode & 0o777) == 0o600
assert text.splitlines()[0].startswith('reopen this scratch session with: ') and 'dependency phase: startup check' in text
rows['first'] = {'seconds': first_s, 'lines': lines, 'line_count': len(lines) - 1, 'log_bytes': log.stat().st_size, 'log_compiling_lines': text.count('Compiling '), 'log_first_line': text.splitlines()[0][:80]}
assert 'DataFrame' in t.send('polars::lit(1)').replace('<::polars::Expr>', 'DataFrame')  # the new session has Polars
first_key = json.loads(json.loads((scratch[0].parent / 'rnx.lock').read_text())['assembly']['identity'])
quit(t)
# A fresh session attaches.
t = session(rnx, env, cwd, splash=True)
t0 = time.monotonic()
_, out = dep(t, ':dep polars', True)
attach_s = round(time.monotonic() - t0, 1)
lines = silent(out, ':dep polars')
rows['attach'] = {'seconds': attach_s, 'line_count': len(lines) - 1}
# PostgreSQL beside Polars, quiet.
t0 = time.monotonic()
_, out = dep(t, ':dep postgres', True)
postgres_s = round(time.monotonic() - t0, 1)
lines = silent(out, ':dep postgres')
rows['postgres'] = {'seconds': postgres_s, 'line_count': len(lines) - 1}
# Asking again for what is installed: nothing.
_, out = dep(t, ':dep polars', True, timeout=120)
assert body(out)[1:] == [], body(out)
assert 'Missing item' not in t.send('postgres::query')
quit(t)
# Verbose: the notice, the prompt, the phases and Cargo's own lines.
t = session(rnx, env, cwd)
notice, out = dep(t, ':depv polars', False)
assert 'New scratch project' in notice and 'Existing bindings and declarations will be lost' in notice
vlines = body(out)
assert 'dependency phase: author' in vlines and any('Locking' in l or 'Updating' in l or 'attached' in l or 'built' in l for l in vlines), vlines
verbose_scratch = sorted((d / 'state/rnx/sessions').glob('session-*/rnx.toml'))[-1]
verbose_key = json.loads(json.loads((verbose_scratch.parent / 'rnx.lock').read_text())['assembly']['identity'])
assert not (verbose_scratch.parent / '.rnx/dep.log').exists(), 'verbose mode writes no log'
rows['verbose'] = {'notice_lines': len(body(notice)), 'line_count': len(vlines), 'first_lines': vlines[:8]}
quit(t)
# The same declaration prepared quietly and verbosely locks to the same key: capture is not an input.
assert first_key == verbose_key, 'quiet and verbose preparations must produce the same identity'
# A quiet failure: offline with no Git checkout in a fresh home: the tail and the log path.
# The home's state directory is group-writable, so the legacy scratch repair notice fires
# before the project exists: it must reach the log and the tail, never the terminal by itself.
d2, env2 = home('offline')
(d2 / 'state/rnx').mkdir(parents=True)
(d2 / 'state/rnx').chmod(0o775)
t = session(rnx, env2, d2 / 'work')
_, out = dep(t, ':dep --offline polars', True, timeout=300)
flines = body(out)[1:]
# The error itself, the actual tail and the log's path: nothing standard around them.
assert flines[0].startswith('resolve: '), flines
assert not any('dependency preparation refused' in l or 'last lines of the output' in l or 'full output:' in l or 'retry with' in l for l in flines), flines
assert any('offline' in l.lower() for l in flines) and flines[-1].endswith('/.rnx/dep.log'), flines
flog = Path(flines[-1]).read_text(errors='replace')
assert 'retry with' in flog, 'the recovery commands are in the log'
assert flog.splitlines()[0].startswith('reopen this scratch session with: ') and 'made scratch directory private' in flog, flog[:400]
assert any('made scratch directory private' in l for l in flines), 'the repair notice is captured output, so a failure shows it in the tail'
assert '42' in t.send('40 + 2'), 'the old session continues'
rows['failure'] = {'lines': flines}
quit(t)
# Ctrl-C during a quiet build returns to the prompt and the session continues.
d3, env3 = home('interrupt')
t = session(rnx, env3, d3 / 'work')
os.write(t.master, b':dep polars\n')
deadline = time.time() + 300
while time.time() < deadline and not list((d3 / 'state/rnx/sessions').glob('session-*/.rnx/dep.log')):
    time.sleep(0.2)
ilog = list((d3 / 'state/rnx/sessions').glob('session-*/.rnx/dep.log'))[0]
while time.time() < deadline and 'dependency phase: build/attach' not in ilog.read_text(errors='replace'):
    time.sleep(0.5)
time.sleep(5)
os.write(t.master, b'\x03')
out = t.read(timeout=120)
ilines = body(out)[1:]
assert ilines == ['^Cinterrupted; old session unchanged'] or ilines == ['interrupted; old session unchanged'], ilines
assert '42' in t.send('40 + 2'), 'the session continues after an interrupted quiet build'
time.sleep(2)
leftover = run(['pgrep', '-fa', str(d3)], check=False).stdout.decode()
leftover = '\n'.join(l for l in leftover.splitlines() if str(t.p.pid) not in l.split(' ', 1)[0])
assert not leftover, f'the build group was not reaped: {leftover}'
rows['interrupt'] = {'lines': ilines, 'no_build_processes_after': True}
quit(t)
assert not run(['pgrep', '-f', 'rnx-project-app|rnx-app-'], check=False).stdout
save('journey.json', rows)
print(f"journey: quiet first build {first_s} s printing nothing, attach {attach_s} s, postgres {postgres_s} s; verbose unchanged; a failure prints the error, the tail and the log; Ctrl-C returns to the prompt; same key either way", flush=True)
