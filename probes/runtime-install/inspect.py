"""Inspect actual installed build inputs after the real journeys, without rerunning builds."""
from pathlib import Path
import json,subprocess as sp,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/runtime-install-0064'
env=json.loads((W/'env.json').read_text());doc=json.loads((O/'installation.json').read_text());C=W/'original';I=Path(json.loads((O/'snapshot.json').read_text())['installed']);store=I.parent.parent.parent

def call(args,cwd=W):
 p=sp.run(list(map(str,args)),env=env,cwd=cwd,capture_output=True,text=True,timeout=120)
 assert p.returncode==0,(args,p.stdout,p.stderr)
 return p.stdout
assert not C.exists()
# Inspect actual locked build inputs and real Cargo metadata, not installation provenance.
inspections=[];forbidden=[str(C),str(B.parent/'rnx'),str(W/'unavailable-original')]
for entry in sorted((W/'cache/entries').iterdir()):
 if not (entry/'ready.json').exists():continue
 manifests=list(entry.glob('**/assembly/Cargo.toml'))
 if not manifests:manifests=[entry/'assembly/Cargo.toml']
 m=manifests[0];assert m.is_file(),list(entry.iterdir())
 main=m.parent/'src/main.rs';meta=call(['cargo','metadata','--locked','--offline','--format-version','1','--manifest-path',m],cwd=m.parent)
 for label,data in [('Cargo manifest',m.read_text()),('wrapper main',main.read_text()),('Cargo metadata',meta)]:
  assert not any(p+suffix in data for p in forbidden for suffix in ['/', '"', '#']),(label,entry)
 metadata=json.loads(meta);locals=[p for p in metadata['packages'] if p['source'] is None]
 for p in locals:
  path=Path(p['manifest_path']);assert path.is_relative_to(I) or path.is_relative_to(entry),path
 (O/(entry.name+'-metadata.json')).write_text(meta)
 inspections.append({'entry':entry.name,'local_manifests':[p['manifest_path'] for p in locals],'no_original_path':True})
assert len(inspections)==2,inspections
locks=list(Path(env['XDG_STATE_HOME']).glob('**/rnx.lock'))+[W/'absolute-project/rnx.lock',W/'relative-project/rnx.lock']
for p in locks:
 lock=json.loads(p.read_text());data=json.dumps(lock['inputs']['native']);assert not any(old+suffix in data for old in forbidden for suffix in ['/', '"', '#']),p
 for tree in lock['inputs']['native']['trees']:assert Path(tree['root']).is_relative_to(I),tree['root']
assert len(locks)==4,len(locks)
for p in [O/'scratch-first.pty',O/'scratch-second.pty']:
 raw=p.read_text();assert 'Runtime: installation '+doc['id'] in raw and str(I) in raw
final=json.loads(call([W/'bin/rnx-project','runtime-probe','fingerprint',I]))
assert final['sha256']==doc['tree_sha256']
fsck=sp.run(['git','-C',str(I),'fsck','--full','--no-reflogs'],env=env,capture_output=True,text=True,timeout=30)
assert fsck.returncode==0,(fsck.stdout,fsck.stderr)
(O/'installed-fsck.log').write_text(fsck.stdout+fsck.stderr)
size=sum(p.stat().st_size for p in store.rglob('*') if p.is_file())
(O/'build-paths.json').write_text(json.dumps({'inspections':inspections,'locks_checked':[str(p) for p in locks],'source_path_absent_through_finish':not C.exists(),'retained_installation_apparent_bytes':size,'installed_git_independent':True,'git_fsck_passes':True,'installed_digest_unchanged_after_builds':True},indent=2)+'\n')
print('PASS installed journeys, cold builds, path inspection and source independence',flush=True)
