"""Pin final drivers and check source correspondence and process cleanup."""
from pathlib import Path
import os, ast, json, hashlib
H=Path(__file__).resolve().parent;B=H.parents[1]
O=Path(os.environ.get('RNX_REMOVAL_RESULTS',str(B/'results/removal-ownership-0066'))).resolve()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in H.glob('*.py'):ast.parse(p.read_text())
d=json.loads((H/'target/real/setup.json').read_text())
stock=Path(os.environ.get('RNX_REMOVAL_OLD_TOOL_SOURCE',str(Path(d['old_tool']).parents[2])))
src=H/'target/real/unavailable-original/tools/project'
files={str(p.relative_to(src)):sha(p) for p in (src/'src').rglob('*.rs')}
assert files and all(sha(stock/n)==v for n,v in files.items())
assert sha(stock/'Cargo.lock')==sha(src/'Cargo.lock')
(O/'old-tool-source.json').write_text(json.dumps(dict(source_revision='7cd3205',sources_sha256=files,lock_sha256=sha(src/'Cargo.lock'),stock_sources_match=True,old_tool_sha256=sha(Path(d['old_tool']))),indent=2)+'\n')
base=str(H/'target');left=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit() or int(p.name)==os.getpid():continue
    try:args=(p/'cmdline').read_bytes().split(b'\0');exe=os.readlink(p/'exe')
    except OSError:continue
    if exe.startswith(base) or any(a.startswith(base.encode()) for a in args):left.append(dict(pid=int(p.name),exe=exe))
mounts=[v for v in Path('/proc/self/mountinfo').read_text().splitlines() if base in v]
assert not left and not mounts,(left,mounts)
(O/'processes.json').write_text(json.dumps(dict(remaining_fixture_processes=left,parent_mounts_under_fixture=mounts),indent=2)+'\n')
(O/'driver-sha256.json').write_text(json.dumps({p.name:sha(p) for p in sorted(H.glob('*')) if p.is_file() and p.suffix in ['.py','.rs']},indent=2)+'\n')
matrix=json.loads((O/'matrix.json').read_text());assert len(matrix['cases'])==44 and all(r['passed'] for r in matrix['cases'])
assert json.loads((O/'journey.json').read_text())['removal']['consumers_reaped_before_removal']
print('PASS source correspondence, 44 cases, live journey, driver hashes and process/mount cleanup')
