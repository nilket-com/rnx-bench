"""Product listing/refusals and manifest publication. No compilation needed."""
from pathlib import Path
import fcntl,hashlib,json,os,signal,subprocess,tempfile,time,tomllib
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/adapter-commands-0062'
T=Path(os.environ.get('RNX_ADAPTER_TOOL',str(R/'tools/project/target/debug/rnx-project')))
ENV={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','RUST','CARGO_'))};rows={};calls=[]
def run(argv,env=None,cwd=None,ok=True):
 p=subprocess.run(list(map(str,argv)),env=env or ENV,cwd=cwd,capture_output=True,text=True,timeout=10)
 calls.append({'args':list(map(str,argv)),'status':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
 assert (p.returncode==0)==ok,(argv,p.returncode,p.stdout,p.stderr)
 return p
def signature(p):
 st=p.stat();return (p.read_bytes(),st.st_ino,st.st_mtime_ns,st.st_mode&0o777)
with tempfile.TemporaryDirectory(prefix='rnx-add-contracts-') as tmp:
 w=Path(tmp);n=w/'runtime';a=w/'app';a.mkdir();n.mkdir()
 (n/'Cargo.toml').write_text('[package]\nname="rnx"\n')
 for name in ['polars','postgres']:
  d=n/'adapters'/name;d.mkdir(parents=True);(d/'Cargo.toml').write_text('[package]\nname="rnx-'+name+'"\n[dependencies]\nrnx={path="../.."}\n')
 m=a/'rnx.toml';base='# preserve this comment\nformat=1\n[application]\nentry="main.rn"\n[runtime]\npath="../runtime"\n'
 def reset(text=base):m.write_text(text);m.chmod(0o640)
 def add(*names,ok=True,extra=None,path=m):return run([T,'add','--manifest',path,*names],dict(ENV,**(extra or {})),ok=ok)
 reset()
 # Helpers are trapped with positive controls. No builder can be invoked via
 # compilation, and fake metadata-only adapters contain no runnable builder.
 traps=w/'bin';traps.mkdir();marker=w/'helper-called'
 for name in ['cargo','rustc','git','curl','wget','cc','ld']:
  p=traps/name;p.write_text('#!/bin/sh\necho called >> "'+str(marker)+'"\nexit 91\n');p.chmod(0o755)
 trapped=dict(ENV,PATH=str(traps)+':'+ENV['PATH'],HOME=str(w/'empty-home'),RNX_PROJECT_CACHE=str(w/'absent-cache'),RUSTFLAGS='must not matter to authoring')
 for name in ['cargo','rustc','git','curl','wget','cc','ld']:assert subprocess.run([name],env=trapped,capture_output=True).returncode==91
 marker.unlink();empty=w/'empty';empty.mkdir()
 listing=run([T,'adapters'],trapped,empty).stdout;assert listing==run([T,'adapters'],trapped,empty).stdout
 assert list(empty.iterdir())==[] and not (w/'empty-home').exists() and not (w/'absent-cache').exists()
 assert 'polars' in listing and 'postgres' in listing and 'lifecycle' in listing
 run([T,'adapters','extra'],trapped,empty,False)
 run(['strace','-f','-e','trace=execve,network','-o',O/'listing.strace',T,'adapters'],trapped,empty)
 run(['strace','-f','-e','trace=execve,network','-o',O/'add.strace',T,'add','polars','--manifest',m],trapped,empty)
 assert not marker.exists()
 for name in ['listing','add']:
  trace=(O/(name+'.strace')).read_text();assert trace.count('execve(')==1 and not any(s in trace for s in ['socket(','connect(','sendto(']),trace
 rows['listing_and_add_no_helpers_or_network']=True
 assert m.read_text().startswith(base) and tomllib.loads(m.read_text())['native']['polars']['path']=='../runtime/adapters/polars'
 same=signature(m);add('polars');assert signature(m)==same
 rows['relative_add_and_true_noop']=True
 # Invalid argv must refuse before Project::open creates its dot-directory.
 clean=w/'clean';clean.mkdir();cm=clean/'rnx.toml';cm.write_text(base)
 for args in [[],['Polars'],['unknown'],['polars','polars'],['polars']*33,['--force','polars'],['--offline','polars'],['--verify','polars'],['--manifest',cm,'polars']]:
  run([T,'add','--manifest',cm,*args],ok=False);assert not (clean/'.rnx').exists()
 for args in [['add','polars'],['add','--manifest'],['add','--manifest',cm,'--']]:run([T,*args],ok=False)
 p=subprocess.run([os.fsencode(T),b'add',b'--manifest',os.fsencode(cm),b'\xff'],env=ENV,capture_output=True,timeout=5);assert p.returncode and not (clean/'.rnx').exists()
 rows['argument_refusals_before_project_open']=True
 # Valid project formats that cannot gain an extension.
 for text in ['format=1\n[source]\nroot="."\n','format=1\n[application]\nentry="main.rn"\n[executable]\npath="binary"\n','format=1\nwrong=true\n']:
  reset(text);before=signature(m);add('polars',ok=False);assert signature(m)==before
 rows['project_kind_and_parser_refusals']=True
 metadata=n/'adapters/polars/Cargo.toml';good=metadata.read_text()
 for label,text,word in [('wrong-name',good.replace('rnx-polars','other'),'package.name'),('inherited-name',good.replace('name="rnx-polars"','name.workspace=true'),'package.name'),('registry-rnx','[package]\nname="rnx-polars"\n[dependencies]\nrnx="1"\n','direct rnx'),('workspace-rnx',good.replace('path="../.."','workspace=true'),'direct rnx'),('wrong-runtime',good.replace('path="../.."','path="."'),'different runtime'),('invalid-toml','[bad','Cargo.toml'),('oversized','#'*(1048577),'1048576')]:
  reset();metadata.write_text(text);before=signature(m);p=add('polars',ok=False);assert word in p.stderr and signature(m)==before,(label,p.stderr)
 metadata.write_text(good)
 for target in [metadata,m]:
  saved=target.read_bytes();target.unlink();os.mkfifo(target);p=add('polars',ok=False);assert 'regular' in p.stderr;target.unlink();target.write_bytes(saved)
 metadata.unlink();reset();p=add('polars',ok=False);assert 'Cargo.toml' in p.stderr;metadata.write_text(good)
 runtime=n/'Cargo.toml';saved=runtime.read_text();runtime.write_text('[package]\nname="wrong"');reset();assert 'package.name' in add('polars',ok=False).stderr;runtime.write_text(saved)
 rows['bounded_regular_metadata_and_layout_refusals']=True
 # One byte over the bound; then a valid at-limit source whose addition crosses it.
 for text in [base+'#'*(1048577-len(base)),base+'#'*(1048576-len(base))]:
  reset(text);before=signature(m);assert '1048576' in add('polars',ok=False).stderr;assert signature(m)==before
 rows['input_and_candidate_size_limits']=True
 # Failure of either member never publishes the other.
 reset();add('postgres');text=m.read_text().replace('builder = "build"','builder = "different"');reset(text);before=signature(m);add('polars','postgres',ok=False);assert signature(m)==before and 'native.polars' not in m.read_text()
 reset('native = {}\n'+base);before=signature(m);assert 'cannot append' in add('polars',ok=False).stderr;assert signature(m)==before
 rows['multi_name_atomic_validation_and_inline_refusal']=True
 reset();add('postgres','polars');assert m.read_text().index('[native.polars]')<m.read_text().index('[native.postgres]') and m.stat().st_mode&0o777==0o640
 rows['sorted_additions_and_permissions']=True
 # Existing declaration cap and reserved names remain the parser's rule.
 native=lambda name: '\n[native.'+name+']\npath="../runtime"\npackage="fixture"\nbuilder="build"\nhook="plain"\n'
 reset(base+''.join(native('n'+str(i)) for i in range(256)));before=signature(m)
 assert 'too many' in add('polars',ok=False).stderr and signature(m)==before
 reset(base+native('std'));before=signature(m);add('polars',ok=False);assert signature(m)==before
 reset();m.write_bytes(b'\xff');before=signature(m);add('polars',ok=False);assert signature(m)==before
 rows['declaration_cap_reserved_name_and_utf8']=True
 # Product path spelling and TOML append cases, after gate one's prototype.
 for prefix in ['[native]\nx={path="../runtime",package="fixture",builder="build",hook="plain"}\n', 'native.x.path="../runtime"\nnative.x.package="fixture"\nnative.x.builder="build"\nnative.x.hook="plain"\n']:
  text=base+prefix if prefix.startswith('[native]') else prefix+base
  reset(text);add('polars');assert m.read_text().startswith(text) and tomllib.loads(m.read_text())['native']['x']['builder']=='build'
 reset(base.rstrip());add('polars');assert m.read_text().startswith(base.rstrip())
 weird=w/'runtime "quote" \\ 🦀';weird.symlink_to(n,target_is_directory=True)
 text=base.replace('"../runtime"',json.dumps(str(weird),ensure_ascii=False));reset(text);add('polars')
 assert tomllib.loads(m.read_text())['native']['polars']['path']==str(weird/'adapters/polars')
 parent=w/'nested';parent.mkdir();(parent/'child').mkdir();(w/'linked').symlink_to(parent/'child',target_is_directory=True)
 (parent/'runtime').symlink_to(n,target_is_directory=True)
 text=base.replace('../runtime','../linked/../runtime');reset(text);add('polars')
 assert tomllib.loads(m.read_text())['native']['polars']['path']=='../linked/../runtime/adapters/polars'
 rows['product_append_and_escaped_symlink_path_spelling']=True
 # No unrelated persisted identity may be touched by adding a declaration.
 reset();protected=[a/'main.rn',a/'rnx.lock',a/'rnx.Cargo.lock',a/'.rnx/receipt.json',a/'.rnx/artifact',a/'.rnx/map.json']
 for p in protected:p.write_text('sentinel '+p.name)
 before={str(p):signature(p) for p in protected};add('polars');assert before=={str(p):signature(p) for p in protected}
 rows['lock_receipt_entry_artifact_and_map_untouched']=True
 # Manifest symlink spelling refers to its resolved target, not a new file.
 reset();link=w/'manifest-link';link.symlink_to(m);add('polars',path=link);assert link.is_symlink() and 'native.polars' in m.read_text()
 rows['manifest_symlink_target']=True
 for kind in ['symlink','fifo','regular']:
  reset();temp=a/'.rnx/add-manifest.new';target=w/'untouched';target.write_text('sentinel')
  if kind=='symlink':temp.symlink_to(target)
  elif kind=='fifo':os.mkfifo(temp)
  else:temp.write_text('old unpublished bytes')
  before=signature(m);assert 'temporary' in add('polars',ok=False).stderr;assert signature(m)==before and target.read_text()=='sentinel' and temp.exists();temp.unlink()
 rows['preexisting_temporary_refused_without_following']=True
 def pause(point):
  marker=w/'pause';marker.unlink(missing_ok=True)
  p=subprocess.Popen([T,'add','--manifest',m,'polars'],env=dict(ENV,RNX_PROJECT_PAUSE=point,RNX_PROJECT_PAUSE_FILE=str(marker)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  deadline=time.monotonic()+10
  while not marker.exists():assert p.poll() is None and time.monotonic()<deadline;time.sleep(.01)
  return p,marker
 for change in ['bytes','replacement','symlink']:
  reset();p,marker=pause('before-add-rename')
  try:
   if change=='bytes':st=m.stat();m.write_text(base.replace('comment','changed'));os.utime(m,ns=(st.st_atime_ns,st.st_mtime_ns))
   elif change=='replacement':replacement=a/'replacement';replacement.write_text(base);replacement.replace(m)
   else:m.unlink();m.symlink_to(protected[0])
   before=m.read_bytes();marker.unlink();out,err=p.communicate(timeout=5);assert p.returncode!=0 and m.read_bytes()==before and not (a/'.rnx/add-manifest.new').exists(),(change,out,err)
  finally:
   if p.poll() is None:p.kill();p.communicate()
   if m.is_symlink():m.unlink()
 rows['editor_change_replacement_and_symlink_refused']=True
 reset();p,marker=pause('before-add-rename')
 try:
  assert 'active' in add('postgres',ok=False).stderr
  marker.unlink();out,err=p.communicate(timeout=5);assert p.returncode==0,(out,err)
 finally:
  if p.poll() is None:p.kill();p.communicate()
 rows['project_writer_exclusion']=True
 for point in ['after-add-temp','before-add-rename','after-add-rename','add-directory-sync']:
  reset();before=signature(m);p=add('polars',ok=False,extra={'RNX_PROJECT_FAIL':point})
  after=point in ['after-add-rename','add-directory-sync']
  assert ('native.polars' in m.read_text())==after
  if after:assert 'was replaced; durability not confirmed' in p.stderr
  else:assert signature(m)==before
  assert not (a/'.rnx/add-manifest.new').exists()
 rows['failure_boundaries_old_or_complete_new']=True
 for point in ['before-add-rename','after-add-rename']:
  for sig in [signal.SIGINT,signal.SIGTERM]:
   reset();before=signature(m);p,marker=pause(point)
   try:
    p.send_signal(sig);out,err=p.communicate(timeout=5);assert p.returncode==128+sig,(out,err)
    if point=='before-add-rename':assert signature(m)==before
    else:assert 'native.polars' in m.read_text() and 'was replaced' in err
    assert not (a/'.rnx/add-manifest.new').exists()
   finally:
    marker.unlink(missing_ok=True)
    if p.poll() is None:p.kill();p.communicate()
 rows['signals_before_and_after_rename']=True
 # No-op does not reach publication, even with a publication fault armed.
 reset();add('polars');before=signature(m);add('polars',extra={'RNX_PROJECT_FAIL':'before-add-rename'});assert signature(m)==before
 rows['noop_bypasses_publication']=True
(O/'contracts.json').write_text(json.dumps(rows,indent=2)+'\n');(O/'contract-calls.json').write_text(json.dumps(calls,ensure_ascii=False,indent=2)+'\n');(O/'adapters.txt').write_text(listing)
print('PASS',len(rows),'listing/refusal/publication groups')
