"""F1: execute the actual printed recovery without rnx-project on PATH."""
from pathlib import Path
import os,subprocess as sp,json,shutil,hashlib,shlex
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target/recovery';O=B/'results/nested-inventory-0065';assert not W.exists();W.mkdir()
OLD=B/'probes/native-inventory/target/stock/tools/project/target/release/rnx-project'
T=W/"bin ' space"/"project ' tool";T.parent.mkdir();shutil.copy2(R/'tools/project/target/release/rnx-project',T)
E={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','RNX_'))};E['XDG_DATA_HOME']=str(W/"data ' space")
s=W/'source';(s/'src').mkdir(parents=True);(s/'Cargo.toml').write_text('[package]\nname="rnx"\nversion="0.0.0"\nedition="2024"\n[workspace]\n');(s/'src/main.rs').write_text('fn main() {}');(s/'src/lib.rs').write_text('// runtime')
for name in ['polars','postgres']:
 p=s/'adapters'/name;(p/'src').mkdir(parents=True);(p/'src/lib.rs').write_text('// adapter');(p/'Cargo.toml').write_text(f'[package]\nname="rnx-{name}"\nversion="0.0.0"\n[workspace]\n[dependencies]\nrnx={{path="../.."}}\n')
for args in [['init','-q'],['add','.']]:sp.run(['git','-C',s,*args],env=E,check=True)
p=sp.run([OLD,'runtime','install','--from',s],env=E,capture_output=True,text=True,check=True);old=p.stdout.split('runtime ',1)[1].splitlines()[0];store=Path(E['XDG_DATA_HOME'])/'rnx/runtimes';entry=store/'entries'/old;s.rename(W/'unavailable')
def snap():return {str(p.relative_to(entry)):[hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_ino,p.stat().st_mtime_ns,p.stat().st_mode] for p in entry.rglob('*') if p.is_file()}
before=snap();selection=(store/'current.json').read_bytes();bin=W/'path';bin.mkdir();(bin/'git').symlink_to(shutil.which('git'));E['PATH']=str(bin);assert shutil.which('rnx-project',path=E['PATH']) is None
lines=[]
for args in [['show'],['select',old]]:
 p=sp.run([T,'runtime',*args],env=E,capture_output=True,text=True);assert p.returncode!=0
 line=next(l for l in p.stderr.splitlines() if ' runtime install --from ' in l)
 assert shlex.split(line)==[str(T),'runtime','install','--from',str(entry/'source')];assert snap()==before and (store/'current.json').read_bytes()==selection;lines.append(line)
p=sp.run(['/bin/sh','-c',lines[0]],env=E,capture_output=True,text=True,timeout=30);assert p.returncode==0,(p.stdout,p.stderr);assert snap()==before
new=json.loads((store/'current.json').read_text())['id'];assert new!=old
(O/'recovery.json').write_text(json.dumps(dict(commands=lines,path=E['PATH'],tool_absent_from_path=True,printed_command_executed=True,old_unchanged=True,new_id=new),indent=2)+'\n')
print('PASS absolute quoted recovery, shell parsed and executed with tool absent from PATH')
