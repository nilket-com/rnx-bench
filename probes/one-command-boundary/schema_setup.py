from common import *
import shutil
D=T/'schema-tool'
if not D.exists():
 D.mkdir();raw=git(R,'archive',BASE,'tools/project').stdout
 import tarfile,io
 with tarfile.open(fileobj=io.BytesIO(raw)) as a:
  for m in a.getmembers():
   m.name=m.name.removeprefix('tools/project/')
   if m.name not in ('tools/project',''):a.extract(m,D,filter='data')
(D/'rustfmt.toml').write_bytes(git(R,'show',BASE+':rustfmt.toml').stdout)
for name in ['schemas.rs','new_identity.rs']:shutil.copy(P/'files'/name,D/'src'/name)
p=D/'src/assembly_probe.rs';s=p.read_text()
if 'mod schemas;' not in s:
 s=s.replace('mod artifact;', 'mod schemas;\nmod new_identity;\nmod artifact;',1)
 s=s.replace('match args.first().and_then(|a| a.to_str()) {','''match args.first().and_then(|a| a.to_str()) {
 Some("schema") if args.len()==4=>{
 let b=std::fs::read(&args[2]).map_err(|e|e.to_string())?;
 let out=schemas::validate(args[1].to_str().ok_or("kind")?,&b)?;
 std::fs::write(&args[3],&out).map_err(|e|e.to_string())?;
 println!("{}",blake3::hash(&out).to_hex());Ok(())
 },''',1);p.write_text(s)
p=D/'src/cache_entry.rs';s=p.read_text()
if 'fn probe_ready' not in s:
 helper='''\npub(crate) fn probe_ready(b:&[u8])->Result<Vec<u8>,String>{
 let r:Ready=serde_json::from_slice(b).map_err(|e|e.to_string())?;
 let identity=Identity::decode(r.identity.as_bytes())?;
 decode_ready(b,&identity,Path::new("/probe/ready.json"))?;
 wire::encode(&r)
}\n''';s=s.replace('#[cfg(test)]\nmod encoding_tests',helper+'\n#[cfg(test)]\nmod encoding_tests',1);p.write_text(s)
run(['cargo','fmt','--manifest-path',D/'Cargo.toml'])
run(['cargo','build','--manifest-path',D/'Cargo.toml','--offline','--locked','--features','test-support','--bin','rnx-project-assembly-probe'],timeout=1200)
for name in ['schemas.rs','new_identity.rs']:shutil.copy(D/'src'/name,P/'files'/name)
print('schema reader built',flush=True)
