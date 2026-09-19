import os,pathlib,subprocess,json,time,shutil
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--work',type=pathlib.Path,required=True,help='new empty fixture directory')
parser.add_argument('--tool',type=pathlib.Path,required=True,help='release rnx-project binary')
args=parser.parse_args()
T=args.work.resolve(); T.mkdir()
R=pathlib.Path(__file__).resolve().parents[3]/'rnx'; tool=args.tool.resolve()
home=T/'cargo';home.mkdir();(home/'registry').symlink_to(pathlib.Path.home()/'.cargo/registry');shutil.copytree(pathlib.Path.home()/'.cargo/git',home/'git')
env={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_','GIT_'))}
env.update(CARGO_HOME=str(home),RNX_PROJECT_CACHE=str(T/'cache'),POLARS_MAX_THREADS='1')
config=home/'config.toml'
slim='[target.x86_64-unknown-linux-gnu]\nlinker = "clang"\nrustflags = ["-C", "link-arg=-fuse-ld=mold"]\n'
rev=subprocess.check_output(['git','rev-parse','0a420d4'],cwd=R,text=True).strip()
manifest=f'''format = 2\n[application]\nentry = "main.rn"\n[runtime]\ngit = "https://github.com/nilket-com/rnx"\nrev = "{rev}"\n[native.polars]\ngit = "https://github.com/nilket-com/rnx"\nrev = "{rev}"\npackage = "rnx-polars"\nbuilder = "build"\nhook = "plain"\n'''
for name in ['slim','plain','patch']:
 p=T/name;p.mkdir();(p/'rnx.toml').write_text(manifest);shutil.copy(R.parent/'rnx-bench/examples/polars/main.rn',p/'main.rn')
def run(name,args,ok=True):
 start=time.monotonic();p=subprocess.run([str(tool),*args],env=env,cwd=T,capture_output=True,text=True,timeout=1200);(T/(name+'.log')).write_text(p.stdout+p.stderr);print(name,p.returncode,round(time.monotonic()-start,2),flush=True)
 if ok and p.returncode:raise RuntimeError(p.stderr[-4000:])
 return p
config.write_text(slim)
run('slim-lock',['lock','--offline','--manifest',str(T/'slim/rnx.toml')])
config.unlink()
run('plain-lock',['lock','--offline','--manifest',str(T/'plain/rnx.toml')])
a=json.loads((T/'slim/rnx.lock').read_text());b=json.loads((T/'plain/rnx.lock').read_text());assert a['assembly']['identity']!=b['assembly']['identity']
left=json.loads(a['assembly']['identity']);right=json.loads(b['assembly']['identity'])
changes=[(x,y) for x,y in zip(left['native']['external'],right['native']['external']) if x!=y]
assert len(changes)==1 and changes[0][0]['path']==str(config)
left['native']['external']=right['native']['external'];assert left==right
(T/'identities.json').write_text(json.dumps({'with_config':a['assembly']['identity'],'without_config':b['assembly']['identity']},indent=2)+'\n')
config.write_text(slim+'[patch.crates-io]\n')
p=run('patch-refusal',['lock','--offline','--manifest',str(T/'patch/rnx.toml')],False);assert p.returncode and 'key patch' in p.stderr;assert not (T/'patch/rnx.lock').exists()
config.write_text(slim)
run('slim-build',['build','--manifest',str(T/'slim/rnx.toml')])
out=T/'output';out.mkdir()
p=run('slim-run',['run','--manifest',str(T/'slim/rnx.toml'),'--',str(out)]);assert (out/'tiny.parquet').exists();assert '🦀' in p.stdout
print('PASS',flush=True)
