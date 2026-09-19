from common import *
s=json.loads((O/'setup.json').read_text());src=Path(s['source']);template=P/'files/build.rs'
# Only collapse equivalent nested ifs; preserve the previously measured commits.
run(['cargo','fmt'],cwd=src)
# Match the formatted source so future preparations recreate the checked code.
template.write_bytes((src/'build.rs').read_bytes())
p=run(['cargo','clippy','--offline','--bin','rnx','--message-format=json'],cwd=src,timeout=1200);(O/'root-clippy.log').write_bytes(p.stdout+p.stderr)
diagnostics=[json.loads(x) for x in p.stdout.splitlines() if x.startswith(b'{')]
warnings=[x['message'] for x in diagnostics if x.get('reason')=='compiler-message' and x['message']['level']=='warning']
assert not any(span['file_name'] in ('build.rs','src/main.rs') for x in warnings for span in x['spans'] if span['is_primary'])
save('root-clippy-existing.json',warnings)
git(src,'add','build.rs');git(src,'-c','user.name=Probe','-c','user.email=probe@example.invalid','commit','--quiet','-m','fixture: collapse equivalent marker guard')
rev=git(src,'rev-parse','HEAD').stdout.decode().strip();git(src,'push','--quiet',s['url'],'HEAD:refs/heads/style-check');git(src,'bundle','create',O/'style-check.bundle','HEAD','^94f5f3f')
(O/'style-check.patch').write_bytes(git(src,'diff',s['rev1'],rev).stdout)
p=run(['cargo','install','--git',s['url'],'--rev',rev,'rnx','--locked','--root',T/'install-style-check','--target-dir',T/'build-target'],timeout=1200);(O/'style-check-install.stderr').write_bytes(p.stderr)
exe=T/'install-style-check/bin/rnx';row=json.loads(run([exe,'--probe-coordinates']).stdout);assert row['state']=='acquired' and row['rev']==rev
assert run([exe,'project','adapters']).stdout==(O/'adapters.stdout').read_bytes()
assert run([exe,'eval','42']).stdout==run([T/'install-git1/bin/rnx','eval','42']).stdout
save('style-check.json',{'revision':rev,'classification':row,'changed':'equivalent nested-if collapse only','management_and_eval_equal':True})
print('Equivalent lint correction passes clippy and real acquired Git installation',flush=True)
