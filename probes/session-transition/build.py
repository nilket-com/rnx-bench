"""Isolate both owners; archive the exact root patch and unchanged imports."""
from pathlib import Path
import hashlib,io,json,shutil,subprocess,tarfile
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/session-transition-0063';W=H/'target';P=W/'root';T=W/'tool'
O.mkdir(exist_ok=True);P.mkdir(parents=True,exist_ok=True);T.mkdir(parents=True,exist_ok=True)
base='bb3477e';data=subprocess.check_output(['git','-C',R,'archive',base])
with tarfile.open(fileobj=io.BytesIO(data)) as a:a.extractall(P,filter='data')
for f in ['Cargo.toml','Cargo.lock']:shutil.copyfile(R/'tools/project'/f,T/f)
shutil.copytree(R/'tools/project/src',T/'src',dirs_exist_ok=True);shutil.copyfile(R/'rustfmt.toml',T/'rustfmt.toml')
shutil.copyfile(H/'tool_probe.rs',T/'src/transition_probe.rs');shutil.copyfile(H/'wire.rs',T/'src/dep_wire.rs')
with (T/'Cargo.toml').open('a') as f:f.write('\n[[bin]]\nname="rnx-transition-tool-probe"\npath="src/transition_probe.rs"\n')
shutil.copyfile(H/'root_transition.rs',P/'src/dep_transition.rs');shutil.copyfile(H/'wire.rs',P/'src/dep_wire.rs')
(P/'src/bin').mkdir(exist_ok=True);shutil.copyfile(H/'fixture.rs',P/'src/bin/rnx-transition-fixture.rs')
f=P/'src/lib.rs';s=f.read_text();s=s.replace('pub use rune;', 'mod dep_transition;\n#[allow(dead_code)]\nmod dep_wire;\npub use rune;',1);s=s.replace('\tmain_inner(extensions)\n','\tdep_transition::installed(extensions.names());\n\tdep_transition::finish(main_inner(extensions))\n',1);f.write_text(s)
f=P/'src/extensions.rs';s=f.read_text().replace('impl Extensions {','impl Extensions {\n    pub(crate) fn names(&self) -> Vec<String> { self.builders.iter().map(|e|e.name.to_owned()).collect() }',1);f.write_text(s)
f=P/'src/repl.rs';s=f.read_text();needle='\tmatch command {\n';assert s.count(needle)==1;s=s.replace(needle,needle+'''        ":dep" => {
            match crate::dep_transition::describe_and_prepare(input) {
                Ok(true) => { println!("restart is beginning"); return Outcome::Quit; },
                Ok(false) => println!("dependency preparation declined"),
                Err(e) => eprintln!("dependency preparation refused: {e}"),
            }
            return Outcome::Continue;
        }
''');f.write_text(s)
for name,path,seed in [('root',P,R/'target'),('tool',T,R/'tools/project/target')]:
 target=path/'target';target.mkdir(exist_ok=True)
 if not (target/'debug').exists():subprocess.run(['cp','-a','--reflink=auto',seed/'debug',target/'debug'],check=True)
 for check,cmd in [('fmt',['cargo','fmt','--manifest-path',str(path/'Cargo.toml')]),('build',['cargo','build','--locked','--offline','--manifest-path',str(path/'Cargo.toml'),'--bin','rnx-transition-fixture' if name=='root' else 'rnx-transition-tool-probe']),('clippy',['cargo','clippy','--locked','--offline','--manifest-path',str(path/'Cargo.toml'),'--bin','rnx-transition-fixture' if name=='root' else 'rnx-transition-tool-probe','--','-D','warnings'])]:
  if name=='root' and check=='clippy':
   cmd.insert(cmd.index('--'),'--message-format=json')
   with (O/'root-clippy.log').open('w') as f:result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
   baseline=['cargo','clippy','--locked','--offline','--manifest-path',str(R/'Cargo.toml'),'--lib','--message-format=json','--','-D','warnings']
   with (O/'baseline-clippy.log').open('w') as f:old_result=subprocess.run(baseline,stdout=f,stderr=subprocess.STDOUT)
   def diagnostics(p):
    out=[]
    for line in p.read_text().splitlines():
     try:j=json.loads(line)
     except ValueError:continue
     if j.get('reason')!='compiler-message':continue
     m=j['message'];spans=[x for x in m['spans'] if x['is_primary']]
     if m['level'] in ['error','warning']:out.append((m['code'],m['message'],[(x['file_name'],x['line_start']) for x in spans]))
    return out
   actual=diagnostics(O/'root-clippy.log');before=diagnostics(O/'baseline-clippy.log')
   assert actual==before and len(before)==13,(actual,before)
   (O/'clippy-baseline.json').write_text(json.dumps({'root_baseline_status':old_result.returncode,'prototype_status':result.returncode,'identical_existing_diagnostics':actual,'new_diagnostics':0},indent=2)+'\n')
  else:
   with (O/(name+'-'+check+'.log')).open('w') as f:result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
   assert result.returncode==0,(name,check)
subprocess.run(['cargo','build','--locked','--offline','--manifest-path',str(P/'Cargo.toml'),'--bin','rnx'],check=True)
# Persist formatted prototype sources; only the named root bridge integration is patched.
for src,dst in [(P/'src/dep_transition.rs',H/'root_transition.rs'),(P/'src/bin/rnx-transition-fixture.rs',H/'fixture.rs'),(T/'src/transition_probe.rs',H/'tool_probe.rs'),(T/'src/dep_wire.rs',H/'wire.rs')]:shutil.copyfile(src,dst)
assert (P/'src/dep_wire.rs').read_bytes()==(H/'wire.rs').read_bytes()
patches=[]
for name in ['src/lib.rs','src/repl.rs','src/extensions.rs']:
 before=subprocess.check_output(['git','-C',R,'show',base+':'+name]).decode();after=(P/name).read_text()
 import difflib
 patches.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(O/'root-integration.patch').write_text(''.join(patches))
imports={}
for source,copy in [(R/'src',P/'src'),(R/'tools/project/src',T/'src')]:
 for f in source.rglob('*.rs'):
  rel=f.relative_to(source);other=copy/rel
  if source==R/'src' and str(rel) in ['lib.rs','repl.rs','extensions.rs']:continue
  assert f.read_bytes()==other.read_bytes(),f
  imports[str(f.relative_to(R))]=hashlib.sha256(f.read_bytes()).hexdigest()
assert (P/'Cargo.lock').read_bytes()==(R/'Cargo.lock').read_bytes()
assert (T/'Cargo.lock').read_bytes()==(R/'tools/project/Cargo.lock').read_bytes()
(O/'imports.json').write_text(json.dumps({'baseline':base,'unchanged_sources':imports,'lockfiles_identical':True},indent=2)+'\n')
print('PASS isolated builds; tool strict Clippy; root baseline diagnostics unchanged; imported sources and graphs unchanged')
