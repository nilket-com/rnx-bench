from common import *
def size(root):
 seen=set();logical=allocated=nodes=0
 for path,dirs,files in os.walk(root,followlinks=False):
  for p in [Path(path),*(Path(path)/f for f in files+[d for d in dirs if (Path(path)/d).is_symlink()])]:
   m=p.lstat();key=(m.st_dev,m.st_ino)
   if key in seen:continue
   seen.add(key);logical+=m.st_size;allocated+=m.st_blocks*512;nodes+=1
 return {'logical_bytes':logical,'allocated_bytes':allocated,'unique_inodes':nodes}
rows=json.loads((O/'roster.json').read_text());env=json.loads((O/'roster-env.json').read_text());out={'cargo_git':size(Path(env['CARGO_HOME'])/'git'),'assemblies':[dict(kind=r['kind'],count=r['count'],key=r['key'],executable_bytes=Path(r['artifact']).stat().st_size,**size(Path(r['artifact']).parent.parent)) for r in rows],'stock_binary':{'bytes':(T/'stock').stat().st_size},'runtime_store_created':False,'registry':'pre-existing shared registry cache, excluded from these deltas','deduplication':'device/inode within each owner; symlinks not traversed; logical includes directory metadata'}
assert not (T/'data').exists();save('storage.json',out)
# Native tree sizes: runtime floor and adapters separately, including overlap.
source=[]
for r in rows:
 if r['kind']!='path':continue
 lock=json.loads(Path(r['manifest']).with_name('rnx.lock').read_text());trees=lock['inputs']['native']['trees'];source.append({'count':r['count'],'trees':[{'root':t['root'],'files':len(t['files']),'bytes':sum(f['bytes'] for f in t['files'])} for t in trees]})
save('native-trees.json',source);print('storage and native sizes recorded')
