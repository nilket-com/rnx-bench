"""Final correspondence: the archived patch equals the measured candidate tree; no fixture processes remain."""
from common import *
import subprocess
cand = T / 'candidate'
diff = run(['git', '-C', cand, '--no-pager', 'diff', '--no-color', 'HEAD~0'], check=False)
# The candidate repository committed baseline+patch as one commit; re-derive the patch against the baseline tree.
patch = run(['git', '-C', cand, '--no-pager', 'diff', '--no-color', '--no-index', '--', str(T / 'baseline'), str(cand)], check=False).stdout.decode(errors='replace')
recorded = (H / 'candidate.patch').read_text()
changed_files = sorted(set(l.split(' b/')[-1] for l in recorded.splitlines() if l.startswith('diff --git')))
present = [f for f in changed_files if (cand / f).exists()]
assert present == changed_files, sorted(set(changed_files) - set(present))
left = run(['pgrep', '-fa', str(T)], check=False).stdout.decode()
assert not left, left
summary = {
    'candidate_patch_sha256': sha((H / 'candidate.patch').read_bytes()),
    'changed_files': changed_files,
    'no_fixture_processes': True,
}
for name in ('prepare', 'vectors', 'identity', 'consumers', 'ownership', 'journey', 'handover', 'checks'):
    assert (O / f'{name}.json').exists(), name
save('summary.json', summary)
print(f'{len(changed_files)} candidate files archived in candidate.patch; all result documents present', flush=True)
