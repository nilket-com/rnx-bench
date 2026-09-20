from common import *
for name in ['prepare', 'vectors', 'identity', 'compatibility', 'control', 'checks']:
    assert (O / f'{name}.json').exists(), name
left = run(['pgrep', '-fa', str(T)], check=False).stdout.decode()
assert not left, left
save('summary.json', {'candidate_patch_sha256': sha((H / 'candidate.patch').read_bytes()), 'documents': sorted(p.name for p in O.iterdir())})
print('all result documents present; no fixture processes remain', flush=True)
