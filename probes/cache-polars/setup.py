"""Fresh real Polars entry, then a second consumer with compilation trapped."""
from common import *
import shutil

O.mkdir(exist_ok=True)
W.mkdir(exist_ok=True)
(O / 'lscpu.txt').write_text(subprocess.check_output(['lscpu'], text=True))
(O / 'uname.txt').write_text(subprocess.check_output(['uname','-a'], text=True))
assert not CACHE.exists(), 'cold build requires a fresh cache; retain/move the old run first'
source = (B / 'examples/polars/main.rn').read_text()
for i, app in enumerate(APPS):
    app.mkdir()
    (app / 'main.rn').write_text(source.replace('    let csv =', f'    println!("consumer-{i+1}");\n    let csv ='))
    (app / 'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath=' + json.dumps(str(R)) + '\n[native.polars]\npath=' + json.dumps(str(R / 'adapters/polars')) + '\npackage="rnx-polars"\nbuilder="build"\nhook="plain"\n')
    dest = O / app.name
    dest.mkdir(exist_ok=True)
    for f in ['main.rn', 'rnx.toml']:
        shutil.copyfile(app / f, dest / f)

costs = {'first_lock_ms': logged('first-lock', command('lock', tail=['--offline']))}
assert not (CACHE / 'entries').exists(), 'lock must not create a compiled entry'
costs['cold_build_ms'] = logged('cold-build', command('build', tail=['--offline']))
a = artifact()
key = receipt(APPS[0])['assembly_key']
assert 'built shared' in (O / 'cold-build.log').read_text()
costs['second_lock_ms'] = logged('second-lock', command('lock', APPS[1], ['--offline']))
lock = json.loads((APPS[1] / 'rnx.lock').read_text())
identity = json.loads(lock['assembly']['identity'])
assert hashlib.sha256(lock['assembly']['identity'].encode()).hexdigest() == key

# Positive controls establish that the trap refuses build/metadata/rustc work.
# Real version observations remain allowed, as the attachment contract requires.
traps = W / 'traps'
traps.mkdir()
trap_log = W / 'compiler-trap.log'
for name, version in [('cargo', '-V'), ('rustc', '-Vv')]:
    real = shutil.which(name)
    script = traps / name
    script.write_text('#!/usr/bin/python3\nimport os,sys\nfrom pathlib import Path\n'
                      f'if sys.argv[1:]==[{version!r}]: os.execv({real!r},[{real!r},*sys.argv[1:]])\n'
                      f'with open({str(trap_log)!r},"a") as f: f.write(repr(sys.argv)+"\\n")\n'
                      'sys.exit(91)\n')
    script.chmod(0o755)
trapped = dict(ENV, PATH=str(traps) + ':' + ENV['PATH'])
for cmd in [['cargo','build'], ['cargo','metadata'], ['rustc','--version']]:
    assert subprocess.run(cmd, env=trapped, capture_output=True).returncode == 91
shutil.copyfile(trap_log, O / 'trap-positive.log')
trap_log.unlink()
costs['ready_attachment_ms'] = logged('second-attach', command('build', APPS[1], ['--offline']), trapped)
assert not trap_log.exists()
assert 'attached shared' in (O / 'second-attach.log').read_text()
assert artifact(APPS[1]) == a
assert receipt(APPS[0])['lock_sha256'] != receipt(APPS[1])['lock_sha256']
assert len(list((CACHE / 'entries').iterdir())) == 1

entry = a.parent.parent
sizes = {}
for name in ['assembly', 'target', 'artifacts']:
    files = [p for p in (entry / name).rglob('*') if p.is_file()]
    sizes[name] = {'files': len(files), 'logical_bytes': sum(p.stat().st_size for p in files),
                   'allocated_bytes': sum(p.stat().st_blocks * 512 for p in files)}
sizes['entry_du_bytes'] = int(subprocess.check_output(['du', '-s', '-B1', str(entry)], text=True).split()[0])
sizes['entry_apparent_bytes'] = int(subprocess.check_output(['du', '-s', '-B1', '--apparent-size', str(entry)], text=True).split()[0])
for app in APPS:
    for f in ['rnx.lock','rnx.Cargo.lock']:
        shutil.copyfile(app / f, O / app.name / f)
    shutil.copyfile(app / '.rnx/receipt.json', O / app.name / 'receipt.json')
shutil.copyfile(entry / 'ready.json', O / 'ready.json')
save('setup.json', {'costs':costs, 'size':sizes, 'cold_target':True, 'downloads':0,
                   'setup_policy':'offline throughout; registry sources already cached; empty entry target, no copied build products',
                   'trap_positive_controls':3, 'attachment_compilations':0,
                   'artifact':str(a), 'artifact_sha256':sha(a), 'artifact_bytes':a.stat().st_size,
                   'tool_sha256':sha(T), 'rnx_head':subprocess.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip(),
                   'bench_base':subprocess.check_output(['git','-C',B,'rev-parse','HEAD'],text=True).strip(),
                   'rustc':subprocess.check_output(['rustc','-Vv'],text=True),
                   'cargo':subprocess.check_output(['cargo','-V'],text=True),
                   'build_affinity':sorted(os.sched_getaffinity(0))})
print(json.dumps({'costs':costs,'size':sizes}, indent=2), flush=True)
