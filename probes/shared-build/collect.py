from common import *
for name in ['runtime-lock', 'assemblies', 'install', 'reuse', 'reuse-sizes', 'lifetime']:
    assert (O / f'{name}.json').exists(), name
cases = {c['case']: c for c in json.loads((O / 'reuse.json').read_text())}
a = cases['a-polars-private']
summary = {'cases': {case: {'seconds': c['seconds'], 'entries': c['compiling_entries'], 'behaviour': c['behaviour'], 'exe_sha256': c['exe_sha256'][:12], 'note': c['note']}
                     for case, c in cases.items()}}
# The preserved control: same bytes as the presenting build, presents frames although the wrapper is plain.
d = cases['d-plain-shared']
summary['wrong_binary_control'] = {'d_equals_c': d['exe_sha256'] == cases['c-polars-shared']['exe_sha256'], 'd_behaviour': d['behaviour']['bare_frame'], 'd_entries': d['compiling_entries']}
assert summary['wrong_binary_control'] == {'d_equals_c': True, 'd_behaviour': 'presents', 'd_entries': 0}
# The remedy: discriminated wrappers behave as written in both orders and on repeats.
for case, expected in [('w1-present-disc', 'presents'), ('w2-plain-disc', 'opaque'), ('w3-present-disc-again', 'presents'), ('w4-plain-disc-again', 'opaque'),
                       ('r1-plain-disc-first', 'opaque'), ('r2-present-disc-second', 'presents'), ('w5-both-disc', 'presents'), ('s2-both-seeded-disc', 'presents')]:
    assert cases[case]['behaviour']['bare_frame'] == expected, (case, cases[case]['behaviour'])
assert cases['w5-both-disc']['behaviour']['postgres'] and cases['s2-both-seeded-disc']['behaviour']['postgres']
assert cases['w3-present-disc-again']['exe_sha256'] == cases['w1-present-disc']['exe_sha256'] and cases['w4-plain-disc-again']['exe_sha256'] == cases['w2-plain-disc']['exe_sha256']
assemblies = json.loads((O / 'assemblies.json').read_text())
summary['overlap'] = {k: {kk: vv for kk, vv in v['overlap'].items() if not isinstance(vv, list)} for k, v in assemblies.items()}
summary['install'] = json.loads((O / 'install.json').read_text())
summary['lifetime'] = json.loads((O / 'lifetime.json').read_text())
summary['sizes'] = json.loads((O / 'reuse-sizes.json').read_text())
save('summary.json', summary)
print(json.dumps({k: (v['seconds'], v['entries'], v['behaviour']['bare_frame']) for k, v in summary['cases'].items()}, indent=1), flush=True)
