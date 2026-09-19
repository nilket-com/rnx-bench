from common import *
s=json.loads((O/'setup.json').read_text());src=Path(s['source']);target=T/'build-target'
ns=['bwrap','--unshare-user','--uid',str(os.getuid()),'--gid',str(os.getgid()),'--unshare-net','--bind','/','/','--dev','/dev','--proc','/proc','--']
# A real Cargo checkout with marker, origin and clean HEAD but no fetched-object
# evidence is unverified. No network calls are allowed to repair classification.
cargo_root=Path(json.loads((O/'first-install.json').read_text())['source'])
fetches=list((T/'cargo-home/git/db').glob('*/FETCH_HEAD'));assert len(fetches)==1
fetch=fetches[0];saved=fetch.read_bytes();fetch.unlink()
try:
 p=run(ns+['cargo','install','--path',cargo_root,'--offline','--locked','--root',T/'install-no-evidence','--target-dir',target],timeout=1200)
 (O/'no-acquisition-evidence.stderr').write_bytes(p.stderr)
 exe=T/'install-no-evidence/bin/rnx';row=json.loads(run([exe,'--probe-coordinates']).stdout);assert row['state']=='unverified',row
 trap=T/'traps';marker=T/'fetch-attempt';assert not marker.exists()
 p=run(ns+['strace','-f','-e','trace=network','-o',O/'no-acquisition-evidence.trace',exe,'--probe-dep'],env=ENV|{'PATH':str(trap)+':'+ENV['PATH']})
 assert b'not yet confirmed reachable' in p.stdout and not marker.exists();assert 'AF_INET' not in (O/'no-acquisition-evidence.trace').read_text()
 save('no-acquisition-evidence.json',row)
finally:fetch.write_bytes(saved)
# Force an actual runner-only compilation, with a functioning Git trap.
trap=T/'no-coordinate-git';trap.mkdir(exist_ok=True);marker=trap/'called';(trap/'git').write_text('#!/bin/sh\ntouch '+str(marker)+'\nexit 99\n');(trap/'git').chmod(0o755)
assert run([trap/'git'],ok=False).returncode==99;marker.unlink()
run(['cargo','clean','--manifest-path',T/'consumer/Cargo.toml','--target-dir',target,'--release','-p','rnx'])
p=run(ns+['cargo','build','--manifest-path',T/'consumer/Cargo.toml','--release','--offline','--target-dir',target],env=ENV|{'PATH':str(trap)+':'+ENV['PATH']},timeout=1200)
assert not marker.exists();(O/'consumer-no-git.stderr').write_bytes(p.stderr)
save('consumer-no-git.json',{'rebuilt':True,'git_trap_positive_control':True,'git_calls':0,'network_disabled':True})
print('Missing acquisition evidence is unverified; runner-only rebuild invokes no Git',flush=True)
