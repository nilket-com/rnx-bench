"""0066 gate-1 prerequisite: unprivileged nested and bind mount fixtures.
No product removal code is imported, built or executed by this preflight.
"""
from pathlib import Path
import hashlib, json, os, shutil, signal, subprocess as sp, sys, tempfile, time
H=Path(__file__).resolve().parent; B=H.parents[1]; R=B.parent/'rnx'; O=B/'results/removal-preflight-0066'
O.mkdir(exist_ok=True)
assert not (O/'preflight.json').exists(), 'preserve the previous result before rerunning'
assert os.geteuid()!=0, 'this gate measures the unprivileged user, not root'
unshare=shutil.which('unshare'); mount=shutil.which('mount'); assert unshare and mount
rows=[]
def run(name,args):
 start=time.monotonic();p=sp.Popen(list(map(str,args)),stdout=sp.PIPE,stderr=sp.PIPE,text=True,start_new_session=True)
 timed_out=False
 try:out,err=p.communicate(timeout=20)
 except sp.TimeoutExpired:
  timed_out=True;os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate()
 row=dict(name=name,args=list(map(str,args)),returncode=p.returncode,stdout=out,stderr=err,timed_out=timed_out,seconds=time.monotonic()-start)
 rows.append(row);print(name,p.returncode,err.strip(),flush=True);return row
parent_ns=os.readlink('/proc/self/ns/mnt')
with tempfile.TemporaryDirectory(prefix='rnx-0066-mount-') as tmp:
 root=Path(tmp)
 for name in ['source','bind','nested']:(root/name).mkdir()
 sentinel=root/'source/sentinel';sentinel.write_bytes(b'outside sentinel\n');before=sentinel.stat()
 run('ordinary-child',[sys.executable,'-c','print("ordinary child works")'])
 run('user-namespace-no-mapping',[unshare,'--user','--fork','true'])
 run('mount-namespace-no-user-mapping',[unshare,'--mount','--fork','true'])
 run('current-user-map',[unshare,'--user','--map-current-user','--mount','--fork','true'])
 actual=run('nested-and-bind-fixture',[unshare,'--user','--map-root-user','--mount','--fork',sys.executable,H/'namespace.py',root,parent_ns,mount])
 entered=(root/'child-entered').exists()
 assert sentinel.read_bytes()==b'outside sentinel\n' and sentinel.stat().st_ino==before.st_ino
 assert not (root/'bind/sentinel').exists() and not (root/'nested/inside').exists(), 'mount leaked into parent namespace'
 assert os.readlink('/proc/self/ns/mnt')==parent_ns
 temp_path=str(root)
assert not Path(temp_path).exists()
status={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in Path('/proc/self/status').read_text().splitlines() if line.split(':',1)[0] in ['Uid','Gid','CapEff','NoNewPrivs','Seccomp','Seccomp_filters']}
result=dict(baseline=sp.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip(),bench_baseline=sp.check_output(['git','-C',B,'rev-parse','HEAD'],text=True).strip(),kernel=dict(release=os.uname().release,machine=os.uname().machine),identity=status,unshare_version=sp.check_output([unshare,'--version'],text=True).strip(),rows=rows,child_entered=entered,mount_fixture_available=actual['returncode']==0,gate1_passed=False,decision='STOP: unprivileged mount fixture unavailable' if actual['returncode'] else 'Prerequisite available; ownership and filesystem prototype still required',product_removal_implemented=False,ordinary_child_passed=rows[0]['returncode']==0,parent_namespace_unchanged=True,outside_sentinel_unchanged=True,temporary_tree_removed=True,privileged_retry=False,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [H/'check.py',H/'namespace.py']})
assert result['ordinary_child_passed']
(O/'preflight.json').write_text(json.dumps(result,indent=2)+'\n')
(O/'product.patch').write_bytes(sp.check_output(['git','-C',R,'diff','--binary','eff151b','--','src','tools/project/src','Cargo.toml','Cargo.lock','tools/project/Cargo.toml','tools/project/Cargo.lock']))
assert not (O/'product.patch').read_bytes()
print(result['decision'],flush=True)
