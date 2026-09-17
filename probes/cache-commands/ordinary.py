from pathlib import Path
import json,os,shutil,subprocess,tempfile
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/cache-commands-0061';T=R/'tools/project/target/release/rnx-project'
with tempfile.TemporaryDirectory(prefix='rnx-shared-ordinary-') as d:
 p=Path(d);n=p/'runtime';shutil.copytree(O/'runtime',n);a=p/'app';a.mkdir();(a/'main.rn').write_text('42');(a/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath="../runtime"\n')
 env={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_'))};env.update(RNX_PROJECT_CACHE=str(p/'cache'),RNX_FIXTURE_BUILD_LOG=str(p/'builds'),RNX_CACHE_FAIL='before-build',RNX_PROJECT_FAIL='after-json-publication')
 for cmd in [['git','init','--quiet',n],['git','-C',n,'add','.']]:subprocess.run(cmd,env=env,check=True)
 for mode,tail in [('lock',['--offline']),('build',['--offline']),('eval',['--','ordinary'])]:
  r=subprocess.run([T,mode,'--manifest',a/'rnx.toml',*tail],env=env,capture_output=True,text=True,timeout=60);assert r.returncode==0,(mode,r.stdout,r.stderr)
 assert 'ordinary' in r.stdout
 assert json.loads((a/'rnx.lock').read_text())['format']==2 and json.loads((a/'.rnx/receipt.json').read_text())['format']==3
 (O/'ordinary.json').write_text(json.dumps({'shared_lock_build_eval':True,'project_and_cache_hooks_absent':True},indent=2)+'\n')
print('PASS ordinary shared commands; fault hooks compiled out')
