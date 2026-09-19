from common import *
rows={}
for kind in ['published','fixture']:
 setup,E=environment(kind);journey=json.loads((O/kind/'journey.json').read_text());assert journey['cleanup']['all_reaped'] and journey['no_runtime_store']=={'created':False,'consulted':False,'trace_sha256':journey['no_runtime_store']['trace_sha256']}
 assert journey['second']['compile_trapped'] and journey['second']['network_disabled']
 dest=O/kind/'documents';dest.mkdir();projects=[]
 for i,manifest in enumerate(sorted(Path(E['XDG_STATE_HOME']).glob('rnx/sessions/*/rnx.toml'))):
  if 'format = 2' not in manifest.read_text():
   assert kind=='published' and str(manifest)==json.loads((O/'selection/result.json').read_text())['path_manifest'];continue
  d=dest/str(i);d.mkdir()
  for name in ['rnx.toml','rnx.lock','rnx.Cargo.lock']:
   p=manifest.parent/name;assert p.is_file();shutil.copy2(p,d/name)
  receipt=manifest.parent/'.rnx/receipt.json';assert receipt.is_file();shutil.copy2(receipt,d/'receipt.json')
  text=(d/'rnx.toml').read_text();lock=(d/'rnx.lock').read_text();assert 'format = 2' in text and setup['rev'] in text and setup['origin'] in text
  assert str(T/'fixture-checkout') not in lock
  projects.append(str(manifest))
 assert len(projects)>=2
 rows[kind]={'projects':projects,'binary_sha256':sha(setup['exe']),'only_binary':sorted(p.name for p in Path(setup['exe']).parent.iterdir()),'origin':setup['origin'],'revision':setup['rev'],'reaped':True}
selection=json.loads((O/'selection/result.json').read_text());assert selection['reaped'] and selection['default_store_not_consulted']
notebook=json.loads((O/'notebook/result.json').read_text());assert notebook['all_reaped']
rows['root']=git(R,'rev-parse','HEAD').stdout.decode().strip();assert not git(R,'diff',REV,'--','.',':(exclude)plans/**').stdout
assert not git(R,'status','--porcelain','--untracked-files=no').stdout
rows['fixture_checkout_absent']=not (T/'fixture-checkout').exists();assert rows['fixture_checkout_absent']
save('checks.json',rows);print('journey evidence checks passed')
