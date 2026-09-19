"""Reproduce the 0068 registration stop without modifying the product checkout."""
import argparse
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

p = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--work', type=Path, required=True, help='absent work directory')
args = parser.parse_args()
work = args.work.resolve()
work.mkdir()
repo = p.parents[1].parent / 'rnx'
revision = json.loads((p / 'baseline.json').read_text())['rnx']
archive = subprocess.check_output(['git', 'archive', revision], cwd=repo)
baseline = work / 'baseline'
baseline.mkdir()
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    tar.extractall(baseline, filter='data')
candidate = work / 'candidate'
shutil.copytree(baseline, candidate)
subprocess.run(['git', 'apply', str(p / 'candidate.patch')], cwd=candidate, check=True)
source = 'fn main() { let _ = rnx::Extensions::none().with("fixture", |_| Err("registration failed".into())); }\n'
for label, root in [('baseline', baseline), ('candidate', candidate)]:
    consumer = work / ('consumer-' + label)
    (consumer / 'src').mkdir(parents=True)
    (consumer / 'src/main.rs').write_text(source)
    (consumer / 'Cargo.toml').write_text(
        '[package]\nname="presentation-compatibility"\nversion="0.0.0"\nedition="2024"\n'
        '[workspace]\n[dependencies]\nrnx={path=' + json.dumps(str(root)) + ',default-features=false}\n')
    result = subprocess.run(['cargo', 'check', '--offline', '--manifest-path', str(consumer / 'Cargo.toml'),
                             '--target-dir', str(work / 'build')], capture_output=True, text=True, timeout=600)
    (work / (label + '.log')).write_text(result.stdout + result.stderr)
    if label == 'baseline':
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0 and 'E0283' in result.stderr and 'Into<Registration>' in result.stderr, result.stderr
    print(label, result.returncode, flush=True)
print('STOP reproduced: the existing failure-only builder requires a new type annotation under the candidate API.')
