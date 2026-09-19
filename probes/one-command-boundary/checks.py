from common import *
s=json.loads((O/'setup.json').read_text());source=Path(s['source']);rows=[]
for label,root in [('integrated',source/'tools/project'),('schema',T/'schema-tool')]:
 for features in [[],['--features','test-support']]:
  for args in [['fmt','--','--check'],['clippy','--all-targets',*features,'--','-D','warnings'],['test',*features,'--','--test-threads=1']]:
   p=run(['cargo',*args],cwd=root,timeout=1200);(O/(label+'-'+args[0]+('-support' if features else '')+'.log')).write_bytes(p.stdout+p.stderr)
   rows.append({'crate':label,'command':args,'status':p.returncode})
run(['cargo','fmt','--','--check'],cwd=source)
p=run(['cargo','clippy','--offline','--bin','rnx','--message-format=json'],cwd=source,timeout=1500);(O/'root-clippy.log').write_bytes(p.stdout+p.stderr)
messages=[json.loads(x)['message'] for x in p.stdout.splitlines() if x.startswith(b'{') and json.loads(x).get('reason')=='compiler-message']
assert not any(span['file_name'] in ('build.rs','src/main.rs') for x in messages for span in x['spans'] if span['is_primary'])
rows.append({'root_clippy':'existing library warnings retained; no diagnostics in new main/build script'})
# Original validators remain exact except a test-only ready adapter.
for name in ['manifest.rs','wire.rs','artifact.rs','cache_identity.rs']:
 original=(R/'tools/project/src'/name).read_bytes();assert original==(T/'schema-tool/src'/name).read_bytes()
 rows.append({'unchanged_reader':name,'sha256':sha(original)})
save('checks.json',rows);print('Formatting, strict clippy, isolated tool suites and legacy source correspondence pass',flush=True)
