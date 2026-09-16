#!/usr/bin/env python3
"""0051: compare complete single-file outputs before matched process timings."""
import hashlib, json, os, pathlib, shlex, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(os.environ.get('RNX_EXTENSION_RESULTS', str(ROOT / 'results/extensions-0051')))
OUT.mkdir(parents=True, exist_ok=True)
before, after, app = (str(pathlib.Path(p).resolve()) for p in sys.argv[1:4])
result = {'binaries': {}, 'outputs': {}, 'versions': {}, 'conditions': {'core': 4, 'warmups': 10, 'runs': 100}, 'sources': {}}
with tempfile.TemporaryDirectory(prefix='rnx modules ') as directory:
    env = dict(os.environ, TERM='xterm', RNX_CONFIG=directory+'/absent', RNX_HISTORY=directory+'/history', NO_COLOR='1')
    for key in list(env):
        if key.startswith('RNX_TEST_') or key == 'RNX_MEMORY_CEILING': env.pop(key, None)
    cases = [
        ('bare', 'pub fn main(_) { 42 }', [], []),
        ('args', 'pub fn main(args) { args }', [], ['abc', '--budget', '3']),
        ('compile', 'pub fn main(_) {\n    let x = ;\n}', [], []),
        ('runtime', 'fn inner() {\n    [1][7]\n}\npub fn main(_) { inner() }', [], []),
        ('method', 'pub fn main(_) { 1.missing() }', [], []),
        ('returned-error', 'pub fn main(_) { Err("bad") }', [], []),
        ('struct', 'struct P { x }\npub fn main(_) { P { x: 42 } }', [], []),
        ('unit', 'pub fn main(_) {}', [], []),
        ('streams', 'pub fn main(_) { print!("out"); io::eprint("err")?; 42 }', [], []),
        ('budget', 'pub fn main(_) { loop {} }', ['--budget', '100'], []),
        ('debug', 'pub fn main(_) { 42 }', ['--debug-source'], []),
        ('debug-error', 'pub fn main(_) { let x = ; }', ['--debug-source'], []),
    ]
    commands = []
    for label, binary in [('before', before), ('after', after), ('app', app)]:
        data = pathlib.Path(binary).read_bytes()
        result['binaries'][label] = {'path': binary, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        for name, source, flags, args in cases:
            path = pathlib.Path(directory) / (name+'.rn')
            path.write_text(source)
            result['sources'][name] = source
            command = [binary, 'run', *flags, str(path), *args]
            r = subprocess.run(command, env=env, capture_output=True, timeout=10)
            result['outputs'][name+' '+label] = {'stdout': r.stdout.decode(), 'stderr': r.stderr.decode(), 'exit': r.returncode}
        for name, args in [('eval-missing', ['eval']), ('run-missing', ['run']), ('file-missing', ['run', directory+'/missing.rn']), ('budget-text', ['run','--budget','bad']), ('budget-zero', ['run','--budget','0']), ('budget-max', ['run','--budget','18446744073709551615'])]:
            r = subprocess.run([binary, *args], env=env, capture_output=True, timeout=10)
            result['outputs'][name+' '+label] = {'stdout': r.stdout.decode(), 'stderr': r.stderr.decode(), 'exit': r.returncode}
        for name, args in [('version', ['version']), ('eval', ['eval', '42']), ('bare run', ['run', str(ROOT/'scripts/bare.rn')]), ('10k JSON', ['run', str(ROOT/'scripts/json.rn')])]:
            r = subprocess.run([binary, *args], env=env, capture_output=True, timeout=10)
            assert r.returncode == 0, (name, r.stderr)
            result['outputs'][name+' '+label] = {'stdout': r.stdout.decode(), 'stderr': r.stderr.decode(), 'exit': r.returncode}
            commands.append((name+' '+label, [binary, *args]))
    for key, expected in result['outputs'].items():
        if key.endswith(' before'):
            name=key.removesuffix(' before')
            for label in ['after', 'app']:
                assert expected == result['outputs'][name+' '+label], (name,label,expected,result['outputs'][name+' '+label])
    for cmd in [['rustc', '--version'], ['cargo', '--version'], ['hyperfine', '--version'], ['uname', '-a']]:
        result['versions'][' '.join(cmd)] = subprocess.check_output(cmd, text=True).strip()
    result['commands'] = commands
    (OUT/'conditions.json').write_text(json.dumps(result, indent=2)+'\n')
    command = ['taskset', '-c', '4', 'hyperfine', '-N', '--warmup', '10', '--runs', '100', '--export-json', str(OUT/'timings.json')]
    for name, args in commands:
        command += ['--command-name', name, shlex.join(args)]
    subprocess.run(command, env=env, check=True)
