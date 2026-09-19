from common import *
import statistics, random, stat
D=json.loads((O/'discovery.json').read_text());root=Path(D['checkout'])
# Raw committed blobs, not status/diff and never filters; bounded to the measured fixture.
def verify(root, rev=REV, hashes=True):
 head=git(root,'rev-parse','HEAD').stdout.decode().strip()
 if head!=rev: raise ValueError('HEAD differs')
 tree=git(root,'ls-tree','-r','-z',rev).stdout
 rows=[]
 for record in tree.split(b'\0'):
  if not record:continue
  header,path=record.split(b'\t',1);mode,kind,oid=header.split()
  if kind!=b'blob' or mode not in [b'100644',b'100755']:raise ValueError('unsupported tree entry')
  name=path.decode();p=root/name
  for parent in [p,*p.parents]:
   if parent==root:break
   if parent.is_symlink():raise ValueError('symlink')
  meta=p.lstat()
  if not stat.S_ISREG(meta.st_mode):raise ValueError('nonregular file')
  if bool(meta.st_mode&0o111)!=(mode==b'100755'):raise ValueError('mode differs')
  rows.append((name,oid.decode()))
 if len(rows)>100000 or sum((root/n).stat().st_size for n,_ in rows)>512*1024*1024:raise ValueError('allowance')
 stage=git(root,'ls-files','--stage','-z').stdout
 staged=[]
 for r in stage.split(b'\0'):
  if not r:continue
  h,n=r.split(b'\t',1)
  if h.split()[-1]!=b'0':raise ValueError('unmerged index')
  staged.append(n.decode())
 if staged!=[n for n,_ in rows]:raise ValueError('tracked set differs')
 extras=git(root,'ls-files','--others','--exclude-standard','-z').stdout.split(b'\0')
 if any(p not in (b'',b'.cargo-ok') for p in extras):raise ValueError('untracked source')
 if hashes:
  for start in range(0,len(rows),64):
   batch=rows[start:start+64]
   got=git(root,'hash-object','--no-filters','--',*[n for n,_ in batch]).stdout.decode().splitlines()
   if got!=[h for _,h in batch]:raise ValueError('raw blob mismatch')
 return len(rows)

def main():
 count=verify(root)
 assert int(run([T/'raw-verify',root,REV]).stdout)==count
 controls={}
 f=root/'README.md';original=f.read_bytes();before=f.stat()
 try:
  edit=bytearray(original);edit[0]^=1;f.write_bytes(edit);os.utime(f,ns=(before.st_atime_ns,before.st_mtime_ns))
  assert run([T/'raw-verify',root,REV],ok=False).returncode!=0
  p=run(['cargo','metadata','--offline','--locked','--format-version=1','--manifest-path',T/'discovery/Cargo.toml'])
  controls['metadata_accepts_modified_checkout']=p.returncode==0
  try:verify(root);raise AssertionError('missed raw mutation')
  except ValueError as e:controls['restored_mtime_edit']=str(e)
 finally:f.write_bytes(original);os.utime(f,ns=(before.st_atime_ns,before.st_mtime_ns))
 # Clean filters cannot turn wrong bytes into a matching raw object.
 attr=root/'.git/info/attributes';attr.parent.mkdir(exist_ok=True);old=attr.read_bytes() if attr.exists() else None
 git(root,'config','filter.probe.clean','cat /dev/null');attr.write_text('README.md filter=probe\n')
 try:
  f.write_bytes(original+b'\n')
  assert run([T/'raw-verify',root,REV],ok=False).returncode!=0
  try:verify(root);raise AssertionError('missed filtered mutation')
  except ValueError as e:controls['hostile_filter']=str(e)
 finally:
  f.write_bytes(original);os.utime(f,ns=(before.st_atime_ns,before.st_mtime_ns))
  if old is None:attr.unlink()
  else:attr.write_bytes(old)
  git(root,'config','--remove-section','filter.probe')
 extra=root/'probe-extra.rs';extra.write_text('untracked')
 try:
  assert run([T/'raw-verify',root,REV],ok=False).returncode!=0
  try:verify(root);raise AssertionError('missed extra')
  except ValueError as e:controls['untracked']=str(e)
 finally:extra.unlink()
 mode=f.stat().st_mode
 try:
  f.chmod(mode^0o111)
  assert run([T/'raw-verify',root,REV],ok=False).returncode!=0
  try:verify(root);raise AssertionError('missed mode')
  except ValueError as e:controls['mode']=str(e)
 finally:f.chmod(mode)
 assert verify(root)==count
 helper=T/'tool/target/release/rnx-project-assembly-probe'
 p=run([helper,'fingerprint-v2','native',root,'100000','536870912'],ok=False)
 controls['existing_path_fingerprinter_on_cargo_checkout']={'status':p.returncode,'stderr':p.stderr.decode()}
 # CPU pinning applies to this process and children, including Git.
 cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
 samples=[]
 functions={
  'coordinates_only':lambda: git(root,'rev-parse','HEAD'),
  'raw_blob_verification':lambda:run([T/'raw-verify',root,REV]),
  'object_fsck':lambda:git(root,'fsck','--full','--no-reflogs'),
  'path_BLAKE3_fingerprint':lambda:run([helper,'fingerprint-v2','native',T/'developer-runtime','100000','536870912']),
 }
 for fn in functions.values():fn()
 for repeat in range(2):
  order=list(functions)*20;random.Random(670001+repeat).shuffle(order)
  for name in order:
   start=time.perf_counter_ns();functions[name]();samples.append({'repeat':repeat,'case':name,'ms':(time.perf_counter_ns()-start)/1e6})
 save('verification.json',{'cpu':cpu,'count':count,'source_bytes':sum((root/n).stat().st_size for n in git(root,'ls-files','-z').stdout.decode().split('\0') if n),'samples':samples,'medians_ms':{k:statistics.median(x['ms'] for x in samples if x['case']==k) for k in functions},'controls':controls,'limits':'Process wall time; raw verification is the compiled Rust probe with Git subprocesses. Not a launch benchmark. fsck is separate, not included in raw verification. Working-tree checks are non-atomic, ignored data/environment remain non-hermetic.'})
 print('Verification passes',flush=True)
if __name__=='__main__':main()
