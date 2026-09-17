"""Real parser/generator authoring; real product lock for assembly-key controls."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,tempfile,tomllib
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/adapter-authoring-0062'
T=H/'target/tool/target/release/rnx-adapter-authoring-probe';TOOL=R/'tools/project/target/release/rnx-project'
E={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_'))}
rows={}
def call(args,env=E,cwd=None):return subprocess.run(list(map(str,args)),env=env,cwd=cwd,capture_output=True,text=True,timeout=120)
def must(args,env=E,cwd=None):
 p=call(args,env,cwd);assert p.returncode==0,(args,p.stdout,p.stderr);return p
def q(s):return json.dumps(str(s),ensure_ascii=False)
def native(name,path):return {'path':str(path),'package':'rnx-'+name,'builder':'build','hook':'plain' if name=='polars' else 'lifecycle'}
def table(name,value):
 # Independent hand-written control: TOML literal strings for the fixture's
 # backslash/quote path, ordinary basic strings for its other values.
 def spelling(v):return "'"+str(v)+"'" if ('\\' in str(v) or '"' in str(v)) and "'" not in str(v) else q(v)
 return '[native.'+name+']\n'+''.join(k+' = '+spelling(v)+'\n' for k,v in value.items())
def layout(root):
 (root/'src').mkdir(parents=True);(root/'src/lib.rs').write_text('// metadata fixture only; no builder or Rune implementation\n')
 (root/'Cargo.toml').write_text('[package]\nname="rnx"\nversion="0.0.0"\nedition="2024"\n[workspace]\n[features]\nproject-sources=[]\n')
 for name in ['polars','postgres']:
  a=root/'adapters'/name;(a/'src').mkdir(parents=True);(a/'src/lib.rs').write_text('// metadata fixture only\n');(a/'Cargo.toml').write_text('[package]\nname="rnx-'+name+'"\nversion="0.0.0"\nedition="2024"\n[workspace]\n[dependencies]\nrnx={path="../.."}\n')
 for name in ['a','z']:
  a=root/'adapters'/name;(a/'src').mkdir(parents=True);(a/'src/lib.rs').write_text('// custom metadata fixture\n');(a/'Cargo.toml').write_text('[package]\nname="custom-'+name+'"\nversion="0.0.0"\nedition="2024"\n[workspace]\n')
 must(['git','init','--quiet',root]);must(['git','-C',root,'add','.'])

with tempfile.TemporaryDirectory(prefix='rnx-authoring-0062-') as tmp:
 root=Path(tmp);cache=root/'cache';env=dict(E,RNX_PROJECT_CACHE=str(cache));n=root/'native';layout(n)
 def case(label,runtime=n,names=('polars','postgres'),spelling=None,prefix='',suffix='',newline=True,identity=True,scope=root):
  d=scope/label;d.mkdir();app=d/'app';manual=d/'manual';app.mkdir();manual.mkdir();out=O/label;out.mkdir(exist_ok=True)
  written=spelling if spelling is not None else os.path.relpath(runtime,app)
  source=prefix+'# application comment stays byte-for-byte\nformat = 1\n[application]\nentry = "main.rn"\n[runtime]\npath = '+q(written)+'\n'+suffix
  if not newline:source=source.rstrip('\n')
  for a in [app,manual]:(a/'main.rn').write_text('pub fn main(_) {42}\n')
  manifest=app/'rnx.toml';manifest.write_text(source);st=manifest.stat();before=manifest.read_bytes()
  p=must([T,manifest,*names],cwd='/');result=json.loads(p.stdout)
  assert manifest.read_bytes()==before and (manifest.stat().st_ino,manifest.stat().st_mtime_ns)==(st.st_ino,st.st_mtime_ns)
  expected=tomllib.loads(source);add=[]
  for name in sorted(names):
   if name not in expected.get('native',{}):add.append(name)
  expected_text=source+('\n\n'+'\n'.join(table(name,native(name,written.rstrip('/')+'/adapters/'+name)) for name in add) if add else '')
  assert result['candidate']==expected_text,(label,result['candidate'],expected_text)
  assert result['candidate'].startswith(source)
  assert result['added']==add
  # Semantic control is independent TOML parsing, then the real Rust parser
  # sees the fully handwritten declaration as an already-present no-op.
  expected.setdefault('native',{}).update({name:native(name,written.rstrip('/')+'/adapters/'+name) for name in add})
  assert tomllib.loads(result['candidate'])==expected
  (manual/'rnx.toml').write_text(expected_text)
  control=json.loads(must([T,manual/'rnx.toml',*names]).stdout)
  assert control['candidate']==expected_text and control['added']==[]
  assert result['manifest']['native']==control['manifest']['native']
  assert result['canonical_wrapper']==control['canonical_wrapper']
  same_base=app/'manual-control.toml';same_base.write_text(expected_text)
  same=json.loads(must([T,same_base,*names]).stdout);same_base.unlink()
  assert result['wrapper']==same['wrapper']
  keys=[]
  if identity:
   manifest.write_text(result['candidate']) # harness materialization, never the probe
   for which,a in [('authored',app),('manual',manual)]:
    p=must([TOOL,'lock','--manifest',a/'rnx.toml','--offline'],env)
    lock=json.loads((a/'rnx.lock').read_text());doc=lock['assembly']['identity'];keys.append(hashlib.sha256(doc.encode()).hexdigest())
    (out/(which+'.identity.json')).write_text(doc+'\n');(out/(which+'.lock.log')).write_text(p.stdout+p.stderr)
    (out/(which+'.Cargo.lock')).write_bytes((a/'rnx.Cargo.lock').read_bytes())
   assert keys[0]==keys[1]
   assert (out/'authored.identity.json').read_bytes()==(out/'manual.identity.json').read_bytes()
  (out/'before.toml').write_text(source);(out/'authored.toml').write_text(result['candidate']);(out/'manual.toml').write_text(expected_text);(out/'probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
  assert not (app/'.rnx/receipt.json').exists() and not (manual/'.rnx/receipt.json').exists()
  rows[label]={'requested':names,'added':add,'same_bytes_as_manual':True,'probe_did_not_write':True,'raw_wrapper_equal_at_same_base':True,'canonical_wrapper_equal':True,'keys':keys}
  print(label,'pass',flush=True);return result
 original_relative=case('relative-both',names=('postgres','polars'))
 case('absolute-both',spelling=str(n))
 case('alternate-relative',spelling='../../native/./')
 case('no-final-newline',names=('polars',),newline=False)
 custom=lambda name:dict(path='../../native/adapters/'+name,package='custom-'+name,builder='build',hook='plain')
 case('comments-and-unsorted',names=('postgres',),suffix='\n'+table('z',custom('z'))+'\n'+table('a',custom('a')))
 case('already-present',names=('polars',),suffix='\n'+table('polars',native('polars','../../native/./adapters/polars')))
 strange=root/'native "quote" \\ 🦀';layout(strange)
 case('escaped-path',runtime=strange)
 bundle=root/'moved-layout';bundle.mkdir();relocated=bundle/'native';shutil.copytree(n,relocated)
 moved_relative=case('relocated-relative',runtime=relocated,scope=bundle)
 assert moved_relative['candidate']==original_relative['candidate']
 assert rows['relocated-relative']['keys'][0]!=rows['relative-both']['keys'][0]
 rows['relocated-relative']['same_manifest_bytes_after_layout_move']=True
 rows['relocated-relative']['new_canonical_identity_requires_relock']=True
 # Resolving link/.. goes to the target's parent, not the lexical parent.
 (n/'child').mkdir();(root/'link').symlink_to(n/'child',target_is_directory=True)
 case('symlink-parent',spelling='../../link/..')
 assert (root/'link/..').resolve()==n and root!=n
 for label,suffix in [('inline-child','\n[native]\npostgres = {path="../../native/adapters/postgres",package="rnx-postgres",builder="build",hook="lifecycle"}\n')]:
  case(label,names=('polars',),suffix=suffix)
 # The native table itself is closed by an inline value and cannot be extended.
 d=root/'closed-inline';d.mkdir();p=d/'rnx.toml';p.write_text('native = {}\nformat=1\n[application]\nentry="main.rn"\n[runtime]\npath="../native"\n');before=p.read_bytes();r=call([T,p,'polars']);assert r.returncode and 'cannot append' in r.stderr and p.read_bytes()==before
 (O/'closed-inline.before.toml').write_bytes(before);(O/'closed-inline.stderr').write_text(r.stderr);rows['closed-inline']={'refused':True,'unchanged':True}
 # Dotted ancestors may allow a new sibling; measure instead of assuming refusal.
 dotted='native.postgres.path="../../native/adapters/postgres"\nnative.postgres.package="rnx-postgres"\nnative.postgres.builder="build"\nnative.postgres.hook="lifecycle"\n'
 case('dotted-sibling',names=('polars',),prefix=dotted)
 case('shipped-polars',runtime=R,names=('polars',))
 case('shipped-postgres',runtime=R,names=('postgres',))
 case('shipped-both',runtime=R)
 assert not (cache/'entries').exists()
 # Archive metadata-only native fixture contents, separate from real packages.
 shutil.copytree(n,O/'metadata-native',dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git'))
(O/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
(O/'conditions.json').write_text(json.dumps({'rnx_head':must(['git','-C',R,'rev-parse','HEAD']).stdout.strip(),'probe_sha256':hashlib.sha256(T.read_bytes()).hexdigest(),'product_tool_sha256':hashlib.sha256(TOOL.read_bytes()).hexdigest(),'scope':'authoring only; fixture writes candidate for real lock equivalence; no compilation or builder execution; publication and command integration deferred','cases':len(rows)},indent=2)+'\n')
print('PASS',len(rows),'authoring cases',flush=True)
