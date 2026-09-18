from pathlib import Path
import hashlib,json,re,subprocess,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/session-preparation-0063'
assert all(json.loads((O/'matrix.json').read_text()).values())
patch=subprocess.check_output(['git','-C',R,'-c','color.ui=false','diff','--cached','--binary','cf6b6bf','--','src','tools/project/src'])
(O/'source.patch').write_bytes(patch)
checks={}
for name in ['root-tests','root-support-tests','root-combined-tests','tool-tests','tool-support-tests']:
 p=Path('/tmp/rnx-0063-'+name+'.log');text=p.read_text();assert 'FAILED' not in text
 counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored',text)
 assert counts
 checks[name]={'passed':sum(int(x[0]) for x in counts),'ignored':sum(int(x[2]) for x in counts)}
 shutil.copyfile(p,O/(name+'.log'))
for name in ['matrix','preparation-final-build']:
 shutil.copyfile('/tmp/rnx-0063-'+name+'.log',O/(name+'.log'))
# Root strict Clippy has the same thirteen previously recorded diagnostics.
items=[]
for line in Path('/tmp/rnx-0063-clippy.json').read_text().splitlines():
 try:j=json.loads(line)
 except ValueError:continue
 if j.get('reason')=='compiler-message' and j['message']['level'] in ['error','warning']:
  m=j['message'];items.append({'code':m['code'],'message':m['message'],'locations':[(s['file_name'],s['line_start']) for s in m['spans'] if s['is_primary']]})
baseline=[]
for line in (B/'results/session-transition-0063/baseline-clippy.log').read_text().splitlines():
 try:j=json.loads(line)
 except ValueError:continue
 if j.get('reason')=='compiler-message' and j['message']['level'] in ['error','warning']:
  m=j['message'];baseline.append({'code':m['code'],'message':m['message'],'locations':[(x['file_name'],x['line_start']) for x in m['spans'] if x['is_primary']]})
assert items==baseline and len(items)==13
checks['root_clippy']={'existing_diagnostics':items,'new_diagnostics':0}
(O/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
receipt=json.loads((W/'project/.rnx/receipt.json').read_text());key=receipt['assembly_key'];app=W/'cache/entries'/key/'artifacts'/receipt['executable_sha256']
files=[R/'tools/project/target/debug/rnx-project',W/'stock-rnx',app]
conditions={'source_baseline':'cf6b6bf','source_patch_sha256':hashlib.sha256(patch).hexdigest(),'platform':subprocess.check_output(['uname','-a'],text=True).strip(),'terminal':{'TERM':'xterm-256color','columns':120},'binaries':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'matrix_groups':len(json.loads((O/'matrix.json').read_text())),'substitutions':['tiny catalogue-shaped adapters; no actual Polars/PostgreSQL engine','manual per-key lock holder','Cargo compilation body waits for cancellation'],'readiness':'disabled until gate 3; no replacement success claim'}
(O/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
# Persist the real validated document schemas used by the positive association.
for name in ['rnx.toml','rnx.lock','rnx.Cargo.lock']:
 shutil.copyfile(W/'project'/name,O/name)
shutil.copyfile(W/'project/.rnx/receipt.json',O/'receipt.json')
print('collected',conditions['matrix_groups'],'groups',checks)
