#!/usr/bin/env python3
"""Release-binary comparison: only the intended fault sentence changes."""
import json, os, pathlib, re, subprocess, sys, tempfile
before, after = map(lambda x: str(pathlib.Path(x).resolve()), sys.argv[1:3])
out = pathlib.Path(__file__).resolve().parents[2] / 'results/method_naming_0041'
rows = []
with tempfile.TemporaryDirectory() as d:
    path = pathlib.Path(d)/'fault.rn'
    path.write_text('pub fn main(_) {\n1.missing()\n}\n')
    cases = [('run', ['run', str(path)], ''),
             ('eval', ['eval', '1.missing()'], ''),
             ('session', [], '1.missing()\n:quit\n'),
             ('retained', [], '()\n()\n()\nlet old = |v| v.missing_method();\n:renumber\n()\nold(1)\n:quit\n'),
             ('chain', ['eval', '"abc".to_uppercase().frobnicate()'], ''),
             ('unknown', ['eval', '#{a: 1}.values().frobnicate()'], '')]
    for name, args, source in cases:
        pair = []
        for label, binary in [('before', before), ('after', after)]:
            p = subprocess.run([binary, '--color=never', *args], input=source, text=True,
                capture_output=True, env=dict(os.environ, TERM='xterm', RNX_HISTORY=d+'/'+label))
            assert p.returncode == (1 if args else 0), p
            pair.append(p)
            rows.append(dict(case=name, build=label, args=args, stdin=source,
                exit=p.returncode, stdout=p.stdout, stderr=p.stderr))
        a, b = pair
        assert a.stdout == b.stdout
        if name in ('run','unknown'):
            assert a.stderr == b.stderr
        else:
            method = {'retained':'missing_method', 'chain':'frobnicate'}.get(name,'missing')
            expected = re.sub(r'Missing instance function `0x[0-9a-f]+` for `([^`]+)`',
                lambda m: f'no method `{method}` on `{m[1]}`', a.stderr)
            assert expected != a.stderr
            assert b.stderr == expected, (name,a.stderr,b.stderr)
(out/'diagnostics.json').write_text(json.dumps(rows,indent=2)+'\n')
print('six release comparisons passed; placement and excerpts byte-identical')
