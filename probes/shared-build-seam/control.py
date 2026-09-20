"""The probe's wrong-binary control and its discriminated series, against the wrappers the candidate
tool actually generated: the baseline's placeholder wrappers reproduce the wrong executable in a
shared directory; the candidate's digest-named wrappers do not, in either order."""
from common import *
import shutil, secrets
url, rev = origin()
work = T / 'control'
work.mkdir(exist_ok=True)
cargo_home = T / 'cargo-home'


def wrapper_dir(name, tool_kind, natives):
    d = project(f'control-{tool_kind}-{name}', natives)
    run([tool(tool_kind), 'lock', '--manifest', d / 'rnx.toml'], cwd=d, env=env_for(T / f'control-cache-{tool_kind}', cargo_home), timeout=900)
    i = identity_of(d)
    out = work / f'{tool_kind}-{name}'
    (out / 'src').mkdir(parents=True)
    (out / 'Cargo.toml').write_text(i['manifest'])
    (out / 'src/main.rs').write_text(i['main'])
    shutil.copy2(d / 'rnx.Cargo.lock', out / 'Cargo.lock')
    return out, package_name(i['manifest'])


def build(src, shared):
    target = src / 'target'
    p = run(['cargo', 'build', '--locked', '--offline', '--release', '--target-dir', target, '--config', f'build.build-dir="{shared}"'],
            cwd=src, env=dict(ENV, CARGO_HOME=str(cargo_home)), timeout=3600)
    entries = re.findall(r'^\s*Compiling ', p.stderr.decode(errors='replace'), re.M)
    exes = [e for e in (target / 'release').iterdir() if e.is_file() and e.name.startswith('rnx-') and not e.suffix]
    return len(entries), exes[0]


def bare_frame(exe):
    cwd = exe.parent
    (cwd / 'sales.csv').write_text('item,qty\napple,3\n')
    cr, pw = os.pipe(); pr, cw = os.pipe()
    p = subprocess.Popen([str(exe), 'worker', '--control-read', str(cr), '--control-write', str(cw)], pass_fds=[cr, cw], stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV, cwd=cwd)
    os.close(cr); os.close(cw)
    send = os.fdopen(pw, 'wb', buffering=0); control = os.fdopen(pr, 'rb', buffering=0)
    n = 0
    def op(kind, source=None):
        nonlocal n
        n += 1
        msg = {'op': kind, 'id': n, 'nonce': secrets.token_hex(32)}
        if source is not None:
            msg['source'] = source
        send.write(json.dumps(msg).encode() + b'\n')
        while True:
            r = json.loads(control.readline(4 * 1024 * 1024))
            if r['type'] == 'settled':
                send.write(json.dumps({'op': 'ack', 'id': n}).encode() + b'\n')
                return r
    assert json.loads(control.readline(4 * 1024 * 1024))['type'] == 'ready'
    op('execute', 'let f = polars::read_csv("sales.csv", [("item","string"),("qty","i64")])?;')
    text = op('execute', 'f')['text_plain']
    op('shutdown')
    assert p.wait(timeout=10) == 0
    return 'presents' if text.startswith('DataFrame: ') else 'opaque' if text == '<::polars::DataFrame>' else text[:60]


present = [('polars', 'rnx-polars', 'plain', 'presentation = true\n')]
plain = [('polars', 'rnx-polars', 'plain', '')]
rows = {}
# Control: the baseline's wrappers share the placeholder name.
b_present, b_name = wrapper_dir('present', 'baseline', present)
b_plain, b_name2 = wrapper_dir('plain', 'baseline', plain)
assert b_name == b_name2 == 'rnx-project-app'
shared = work / 'shared-baseline'
n1, e1 = build(b_present, shared)
n2, e2 = build(b_plain, shared)
rows['baseline'] = {'present': {'entries': n1, 'behaviour': bare_frame(e1)}, 'plain': {'entries': n2, 'behaviour': bare_frame(e2), 'same_bytes_as_present': sha(e2.read_bytes()) == sha(e1.read_bytes())}}
assert rows['baseline']['plain'] == {'entries': 0, 'behaviour': 'presents', 'same_bytes_as_present': True}, rows
# The candidate's wrappers carry their digest names: correct in both orders.
c_present, c_name = wrapper_dir('present', 'candidate', present)
c_plain, c_name2 = wrapper_dir('plain', 'candidate', plain)
assert c_name != c_name2 and c_name.startswith('rnx-app-') and c_name2.startswith('rnx-app-')
shared = work / 'shared-candidate'
n1, e1 = build(c_present, shared)
n2, e2 = build(c_plain, shared)
n3, e3 = build(c_present, shared)
rows['candidate'] = {'present': {'entries': n1, 'behaviour': bare_frame(e1)}, 'plain': {'entries': n2, 'behaviour': bare_frame(e2)},
                     'present_again': {'entries': n3, 'behaviour': bare_frame(e3), 'same_bytes': sha(e3.read_bytes()) == sha(e1.read_bytes())}, 'names': [c_name, c_name2]}
assert rows['candidate']['plain'] == {'entries': 1, 'behaviour': 'opaque'} and rows['candidate']['present_again'] == {'entries': 0, 'behaviour': 'presents', 'same_bytes': True}, rows
shared = work / 'shared-candidate-reverse'
n1, e1 = build(c_plain, shared)
n2, e2 = build(c_present, shared)
rows['candidate-reverse'] = {'plain': {'entries': n1, 'behaviour': bare_frame(e1)}, 'present': {'entries': n2, 'behaviour': bare_frame(e2)}}
assert rows['candidate-reverse']['plain']['behaviour'] == 'opaque' and rows['candidate-reverse']['present'] == {'entries': 1, 'behaviour': 'presents'}, rows
save('control.json', rows)
print('control: the baseline wrappers reproduce the wrong executable; the candidate wrappers build one unit and behave as written in both orders', flush=True)
