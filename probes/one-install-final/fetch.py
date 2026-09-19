from common import *
import re,gzip
row=json.loads((B/'results/one-install-0067/published/journey.json').read_text())['combined'];assembly=Path(row['artifact']).parent.parent/'assembly';d=T/'fetch-project';(d/'src').mkdir(parents=True)
for name in ['Cargo.toml','Cargo.lock']:shutil.copy2(assembly/name,d/name)
shutil.copy2(assembly/'src/main.rs',d/'src/main.rs');rows=[]
for mode in ['untraced','transport-trace']:
 home=T/('fetch-'+mode);home.mkdir();(home/'registry').symlink_to(Path.home()/'.cargo/registry',target_is_directory=True);env=ENV|{'CARGO_HOME':str(home)}
 command=['cargo','fetch','--locked','--target','x86_64-unknown-linux-gnu','--manifest-path',d/'Cargo.toml']
 p=run([*command,'--offline'],env=env,ok=False);assert p.returncode and b'offline' in p.stderr;(O/('fetch-'+mode+'-offline.log')).write_bytes(p.stderr)
 if mode=='transport-trace':command=['strace','-f','-qq','-s','0','-yy','-o',O/'fetch.trace','-e','trace=read,recvfrom,recvmsg',*command]
 start=time.monotonic();p=run(command,env=env);seconds=time.monotonic()-start;(O/('fetch-'+mode+'.log')).write_bytes(p.stdout+p.stderr)
 packs=list((home/'git/db').glob('*/objects/pack/*.pack'));pack_bytes=sum(p.stat().st_size for p in packs)
 rows.append({'mode':mode,'seconds':seconds,'git_pack_bytes':pack_bytes,'pack_count':len(packs),'cargo_home':str(home),'registry_cache':'shared preexisting; Git DB/checkout initially absent'})
 if mode=='transport-trace':
  trace=O/'fetch.trace';lines=trace.read_text().splitlines();tcp=[l for l in lines if '<TCP:' in l and re.search(r'= [1-9][0-9]*$',l)];rows[-1]['tcp_received_bytes']=sum(int(re.search(r'= ([0-9]+)$',l).group(1)) for l in tcp);rows[-1]['tcp_read_calls']=len(tcp);rows[-1]['trace_sha256']=sha(trace);trace.with_suffix('.trace.gz').write_bytes(gzip.compress(trace.read_bytes(),mtime=0));trace.unlink()
save('fetch.json',rows);print('fetch observed',flush=True)
