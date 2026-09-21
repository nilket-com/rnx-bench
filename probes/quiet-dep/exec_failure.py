"""A cleanup or exec failure after the commitment is still named under `:dep`: a test-support session
pauses before exec, the artifact is moved away, and the release produces the named error."""
from common import *
prep = json.loads((O / 'prepare.json').read_text())
support = prep['binaries']['product-support']['path']
d, env = home('quiet')  # Polars is built there: the quiet request attaches
marker = d / 'exec-marker'
release = d / 'exec-release'
for p in (marker, release):
    p.unlink(missing_ok=True)
t = session(support, env, d / 'work', {'RNX_DEP_PAUSE': 'before-exec', 'RNX_DEP_MARKER': str(marker), 'RNX_DEP_RELEASE': str(release)})
os.write(t.master, b':dep polars\n')
deadline = time.time() + 300
while time.time() < deadline and not marker.exists():
    if select.select([t.master], [], [], .05)[0]:
        t.log += os.read(t.master, 65536)
    time.sleep(0.05)
assert marker.exists(), 'the session must pause before exec'
artifact = Path(marker.read_text())
assert artifact.is_file()
before = terminal.text(t.log)
assert body(before)[1:] == [], body(before)  # nothing printed up to the pause
moved = artifact.with_name(artifact.name + '.held')
artifact.rename(moved)
release.write_text('go')
out = t.read(False, timeout=60)
lines = body(out)
assert any('artifact changed before dependency restart' in l or 'dependency restart' in l for l in lines), lines
assert t.p.wait(timeout=30) != 0, 'a failure after the commitment is terminal'
moved.rename(artifact)
t.close()
save('exec_failure.json', {'paused_at': 'before-exec', 'printed': lines[:4], 'terminal': True})
print('exec failure: named under :dep after the commitment, and terminal, as before', flush=True)
