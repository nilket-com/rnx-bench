from common import *
import tarfile,io,shutil
baseline='94f5f3f98ba756c5ab5293d1e5132c7fd7b52d32';old=T/'legacy';old.mkdir()
archive=git(R,'archive',baseline,'tools/project').stdout
tarfile.open(fileobj=io.BytesIO(archive)).extractall(old,filter='data')
r=run(['cargo','build','--offline','--locked','--manifest-path',old/'tools/project/Cargo.toml','--bin','rnx-project']);(O/'legacy-build.log').write_bytes(r.stderr);oldtool=old/'tools/project/target/debug/rnx-project'
p=T/'legacy-app';p.mkdir();(p/'main.rn').write_text('pub fn main(_) {}\n');(p/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath='+json.dumps(str(T/'tiny-source-clean'))+'\n')
for op in ['lock','build']:run([oldtool,op,'--offline','--manifest',p/'rnx.toml'])
files=[p/'rnx.lock',p/'rnx.Cargo.lock',p/'.rnx/receipt.json'];before=[x.read_bytes() for x in files];receipt=json.loads(before[-1]);key=receipt['assembly_key'];entry=Path(ENV['RNX_PROJECT_CACHE'])/'entries'/key;ready=(entry/'ready.json').read_bytes();oldinode=(entry/'artifacts'/receipt['executable_blake3']).stat().st_ino
for op in ['eval','session']:
 r=run([TOOL,op,'--manifest',p/'rnx.toml']+(['--','42'] if op=='eval' else []));assert b'fixture runtime' in r.stdout
assert before==[x.read_bytes() for x in files]
# Explicit relock uses the contemporary generator, never promotes old readiness.
run([TOOL,'lock','--offline','--manifest',p/'rnx.toml']);r=run([TOOL,'eval','--manifest',p/'rnx.toml','--','42'],ok=False);assert r.returncode and b'run build' in r.stderr
run([TOOL,'build','--offline','--manifest',p/'rnx.toml']);newreceipt=json.loads(files[-1].read_bytes());assert newreceipt['assembly_key']!=key;assert (entry/'ready.json').read_bytes()==ready and (entry/'artifacts'/receipt['executable_blake3']).stat().st_ino==oldinode
run([TOOL,'cache','list','--manifest',p/'rnx.toml']);run([TOOL,'cache','remove',key,'--dry-run']);run([TOOL,'cache','remove',key,'--quiescent']);assert not entry.exists();run([TOOL,'eval','--manifest',p/'rnx.toml','--','42'])
save('legacy.json',{'baseline':baseline,'old_key':key,'new_key':newreceipt['assembly_key'],'ordinary_launch_preserved_documents':True,'explicit_relock_no_promotion':True,'old_entry_explicitly_removed':True,'new_entry_still_runs':True})
print('Genuine retained path envelopes, relock and removal pass',flush=True)
