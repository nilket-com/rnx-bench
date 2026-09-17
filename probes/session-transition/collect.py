from pathlib import Path
import ast,hashlib,json,os,subprocess
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/session-transition-0063'
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
assert all(json.loads((O/'results.json').read_text()).values())
assert len(json.loads((O/'ordinary-entry.json').read_text()))==7
assert json.loads((O/'clippy-baseline.json').read_text())['new_diagnostics']==0
assert '1 passed; 0 failed' in (O/'protocol-unit.log').read_text()
protected=['src','Cargo.toml','Cargo.lock','THIRD-PARTY-NOTICES.md','tools','adapters','jupyter','servers']
assert not subprocess.check_output(['git','-C',R,'diff','bb3477e','--',*protected])
active=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:exe=os.readlink(p/'exe')
 except OSError:continue
 if str(H/'target') in exe:active.append((p.name,exe))
assert not active,active
files={}
for p in list(H.glob('*.rs'))+list(H.glob('*.py'))+[O/'root-integration.patch']:
 files[str(p.relative_to(B))]=hashlib.sha256(p.read_bytes()).hexdigest()
bins={}
for name,p in [('stock-prototype',H/'target/root/target/debug/rnx'),('lifecycle-prototype',H/'target/root/target/debug/rnx-transition-fixture'),('tool-prototype',H/'target/tool/target/debug/rnx-transition-tool-probe')]:
 with p.open('rb') as f:bins[name]=hashlib.file_digest(f,'sha256').hexdigest()
(O/'conditions.json').write_text(json.dumps({'baseline':'bb3477e','sources':files,'binaries':bins,'product_protected_paths_unchanged':True,'active_fixture_processes':active,'platform':'Linux, Unix socket controls; no Windows execution or timing claim','rustc':subprocess.check_output(['rustc','-Vv'],text=True)},indent=2)+'\n')
print('PASS evidence checks, unchanged product and no surviving fixture executables')
