"""Declaration vectors: `presentation` omitted/false/true, invalid, unknown, across formats and hooks."""
from common import *
probe = tool('candidate-probe')
base = tool('baseline')
work = T / 'vectors'
work.mkdir(exist_ok=True)
runtime = T / 'candidate'
GIT = 'https://github.com/nilket-com/rnx'
REV = 'b5664ff5400d8dad8c44f39b3c52832d954ab7b1'


def native(fmt, hook, extra):
    loc = f'path = "adapters/polars"' if fmt == 1 else f'git = "{GIT}"\nrev = "{REV}"'
    return f'[native.polars]\n{loc}\npackage = "rnx-polars"\nbuilder = "build"\nhook = "{hook}"\n{extra}'


def manifest(fmt, hook, extra):
    rt = f'[runtime]\npath = "."' if fmt == 1 else f'[runtime]\ngit = "{GIT}"\nrev = "{REV}"'
    return f'format = {fmt}\n[application]\nentry = "main.rn"\n{rt}\n{native(fmt, hook, extra)}'


def canonical(name, text):
    src = work / f'{name}.toml'
    out = work / f'{name}.bin'
    src.write_text(text)
    p = run([probe, 'schema', 'declaration', src, out], check=False)
    return (p.returncode, p.stdout.decode().strip(), p.stderr.decode().strip(), out.read_bytes() if out.exists() else b'')


results = {}
for fmt in (1, 2):
    for hook in ('plain', 'lifecycle'):
        omitted = canonical(f'f{fmt}-{hook}-omitted', manifest(fmt, hook, ''))
        false = canonical(f'f{fmt}-{hook}-false', manifest(fmt, hook, 'presentation = false\n'))
        true = canonical(f'f{fmt}-{hook}-true', manifest(fmt, hook, 'presentation = true\n'))
        assert omitted[0] == 0 and false[0] == 0 and true[0] == 0, (omitted, false, true)
        assert omitted[3] == false[3], 'false must canonicalize to the omitted bytes'
        assert omitted[3] != true[3], 'true must change the canonical bytes'
        assert b'presentation' in true[3] and b'presentation' not in omitted[3]
        refusals = {}
        for label, extra in [('string', 'presentation = "yes"\n'), ('integer', 'presentation = 1\n'),
                             ('unknown', 'presentation = true\ndisplay = true\n'), ('duplicate', 'presentation = true\npresentation = false\n')]:
            code, out, err, _ = canonical(f'f{fmt}-{hook}-{label}', manifest(fmt, hook, extra))
            assert code != 0, (label, out)
            refusals[label] = err[:200]
        results[f'format{fmt}-{hook}'] = {
            'omitted_sha256': sha(omitted[3]), 'false_sha256': sha(false[3]), 'true_sha256': sha(true[3]),
            'false_equals_omitted': True, 'true_differs': True, 'refusals': refusals}
# The baseline tool (b5664ff) refuses a declaration carrying the field, naming it.
for fmt in (1, 2):
    project = work / f'old-tool-format{fmt}'
    project.mkdir(exist_ok=True)
    (project / 'main.rn').write_text('pub fn main(_) { 42 }\n')
    if fmt == 1:
        text = manifest(1, 'plain', 'presentation = true\n').replace('path = "."', f'path = "{runtime}"').replace('path = "adapters/polars"', f'path = "{runtime}/adapters/polars"')
    else:
        text = manifest(2, 'plain', 'presentation = true\n')
    (project / 'rnx.toml').write_text(text)
    p = run([base, 'lock', '--manifest', project / 'rnx.toml', '--offline'], check=False, env=dict(ENV, RNX_PROJECT_CACHE=str(work / 'old-cache')))
    err = p.stderr.decode()
    assert p.returncode != 0 and 'presentation' in err, err
    assert not (project / 'rnx.lock').exists(), 'the old tool must not publish a lock'
    results[f'baseline-tool-refuses-format{fmt}'] = err.strip()[:300]
save('vectors.json', results)
print(f'{len(results)} declaration vector groups pass', flush=True)
