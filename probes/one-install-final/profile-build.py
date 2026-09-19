from common import *
source=T/'profile-source';run(['git','clone','--quiet','--no-hardlinks',R,source]);run(['git','checkout','--quiet','--detach','1b894e0'],cwd=source)
args=['cargo','build','--release','--locked','--offline','--manifest-path','tools/project/Cargo.toml','--bin','rnx-project','-j','4']
p=run(args,cwd=source);(O/'profile-control-build.log').write_bytes(p.stderr);shutil.copy2(source/'tools/project/target/release/rnx-project',T/'profile-control')
f=source/'tools/project/src/workflow/git_sources.rs';s=f.read_text();needle='\tpub(super) fn git_launch(self, mode: Launch, verify: bool) -> Result<(), String> {\n';assert s.count(needle)==1;s=s.replace(needle,needle+'\t\tlet __start=std::time::Instant::now();\n')
for old,new in [('let (lock, bytes) = self.read_git_lock()?;','let (lock, bytes) = self.read_git_lock()?;\n\t\tlet __read=__start.elapsed().as_nanos();'),('self.git_verify_inputs(&lock, verify)?;','self.git_verify_inputs(&lock, verify)?;\n\t\tlet __inputs=__start.elapsed().as_nanos();'),('let (checked, digest) = self.git_checked_artifact(&lock, &bytes, verify, true)?;','let (checked, digest) = self.git_checked_artifact(&lock, &bytes, verify, true)?;\n\t\tlet __artifact=__start.elapsed().as_nanos();')]:
 # Instrument only the launch function; keep build/resolve code identical.
 i=s.index(needle);head,tail=s[:i],s[i:];assert old in tail;tail=tail.replace(old,new,1);s=head+tail
old='\t\t// Advisory lock descriptors are close-on-exec;';assert s.count(old)==1
s=s.replace(old,'''\t\tlet __command=__start.elapsed().as_nanos();
        if let Some(path)=std::env::var_os("RNX_GATE_PROFILE") {
            let mut f=std::fs::OpenOptions::new().append(true).create(true).open(path).map_err(err)?;
            writeln!(f,"{}",serde_json::json!({"read_lock_ns":__read,"inputs_ns":__inputs-__read,"artifact_ns":__artifact-__inputs,"command_ns":__command-__artifact,"total_ns":__command})).map_err(err)?;
        }
'''+old)
f.write_text(s);run(['cargo','fmt','--manifest-path','tools/project/Cargo.toml'],cwd=source)
(O/'profile.patch').write_bytes(run(['git','-c','color.ui=false','diff','--binary'],cwd=source).stdout)
p=run(args,cwd=source);(O/'profile-build.log').write_bytes(p.stderr);shutil.copy2(source/'tools/project/target/release/rnx-project',T/'profiled')
save('profile-binaries.json',{k:{'path':str(T/k),'sha256':sha(T/k)} for k in ['profile-control','profiled']});print('profiling tools ready',flush=True)
