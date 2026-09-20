"""The `shared_build` declaration through the real readers: omitted, false and true keep or change
canonical bytes; wrong types and unknown siblings refuse; the baseline tool refuses the field by name."""
from common import *
probe = tool('candidate-probe')
work = T / 'vectors'
work.mkdir(exist_ok=True)


def canonical(text):
    src = work / f'{sha(text.encode())[:12]}.toml'
    src.write_text(text)
    out = work / (src.stem + '.out')
    p = run([probe, 'schema', 'declaration', src, out], check=False)
    return (True, out.read_bytes()) if p.returncode == 0 else (False, p.stderr.decode(errors='replace'))


results = {}
for fmt in [1, 2]:
    for hook in ['plain', 'lifecycle']:
        if fmt == 1:
            head = 'format = 1\n[application]\nentry = "main.rn"\n[runtime]\npath = "../rnx"\n[native.x]\npath = "../rnx/adapters/x"\npackage = "rnx-x"\nbuilder = "build"\n'
        else:
            head = 'format = 2\n[application]\nentry = "main.rn"\n[runtime]\ngit = "https://example.invalid/rnx"\nrev = "0123456789abcdef0123456789abcdef01234567"\n[native.x]\ngit = "https://example.invalid/rnx"\nrev = "0123456789abcdef0123456789abcdef01234567"\npackage = "rnx-x"\nbuilder = "build"\n'
        head += f'hook = "{hook}"\n'
        omitted = canonical(head)
        false = canonical(head + 'shared_build = false\n')
        true = canonical(head + 'shared_build = true\n')
        both = canonical(head + 'presentation = true\nshared_build = true\n')
        assert omitted[0] and false[0] and true[0] and both[0], (omitted, false, true, both)
        assert omitted[1] == false[1], 'false must canonicalize to the omitted bytes'
        assert true[1] != omitted[1] and b'"shared_build":true' in true[1]
        assert b'"presentation":true' in both[1] and b'"shared_build":true' in both[1]
        refusals = {}
        for label, text in [('string', 'shared_build = "yes"\n'), ('integer', 'shared_build = 1\n'), ('unknown-sibling', 'shared_build = true\nshared = true\n'),
                            ('duplicate', 'shared_build = true\nshared_build = true\n')]:
            ok, msg = canonical(head + text)
            assert not ok, (fmt, hook, label)
            refusals[label] = msg.strip()[:160]
        results[f'format{fmt}-{hook}'] = {'omitted_equals_false': True, 'true_bytes': true[1].decode(), 'refusals': refusals}
# The baseline tool refuses the field by name before publishing a lock.
d = T / 'vectors' / 'baseline-project'
d.mkdir(exist_ok=True)
(d / 'main.rn').write_text('pub fn main(_) { 42 }\n')
url, rev = origin()
(d / 'rnx.toml').write_text(f'format = 2\n[application]\nentry = "main.rn"\n[runtime]\ngit = "{url}"\nrev = "{rev}"\n[native.polars]\ngit = "{url}"\nrev = "{rev}"\npackage = "rnx-polars"\nbuilder = "build"\nhook = "plain"\nshared_build = true\n')
p = run([tool('baseline'), 'lock', '--manifest', d / 'rnx.toml', '--offline'], cwd=d, env=env_for(T / 'vectors/cache', T / 'cargo-home'), check=False)
message = p.stderr.decode(errors='replace')
assert p.returncode != 0 and 'shared_build' in message and not (d / 'rnx.lock').exists(), message
results['baseline_refusal'] = message.strip()[-300:]
save('vectors.json', results)
print('shared_build vectors: omitted equals false, true changes bytes, wrong types and unknown siblings refuse; the baseline tool refuses by name', flush=True)
