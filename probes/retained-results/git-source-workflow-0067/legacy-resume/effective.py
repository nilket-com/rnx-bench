"""A real old tool rebuilds the same key while its previous entry is pending."""
from pathlib import Path
import os,json,subprocess as sp,time,hashlib,stat,selectors,signal
H=Path(__file__).resolve().parent;B=H.parents[1];W=Path('/home/me/work/rnx-bench/probes/git-source-workflow/target/legacy-resume');O=Path('/home/me/work/rnx-bench/results/git-source-workflow-0067/legacy-resume')
T=Path('/home/me/work/rnx-bench/probes/git-source-workflow/target/rnx-project');d=json.loads((W/'setup.json').read_text());E=json.loads((W/'env.json').read_text())
old=Path(d['old_tool']);artifact=Path(d['artifact']);entry=artifact.parent.parent;key=entry.name;cache=entry.parent.parent;m=Path(d['old_manifest'])
assert not (O/'rebuild.json').exists()
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(1048576):h.update(b)
    return h.hexdigest()
def snap(p):
    out={}
    for base,ds,fs in os.walk(p,followlinks=False):
        for n in ds+fs:
            q=Path(base)/n;s=q.lstat();out[str(q.relative_to(p))]=(s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,sha(q) if stat.S_ISREG(s.st_mode) else os.readlink(q) if stat.S_ISLNK(s.st_mode) else None)
    return out
def call(a,timeout=1200):
    p=sp.run(list(map(str,a)),env=E,cwd=W,capture_output=True,text=True,timeout=timeout);assert p.returncode==0,(p.returncode,p.stdout,p.stderr);return p
before_receipt=(m.parent/'.rnx/receipt.json').read_bytes();before_locks={n:(m.parent/n).read_bytes() for n in ['rnx.lock','rnx.Cargo.lock']};old_inode=artifact.stat().st_ino
# The real receipt annotates the entry before removal, without changing it.
v=json.loads(call([T,'cache','list','--root',cache,'--manifest',m]).stdout);assert v['entries'][0]['referenced_by']==[str(m)]
args=[T,'cache','remove',key,'--root',cache,'--quiescent']
p=sp.Popen(list(map(str,args)),env=dict(E,RNX_REMOVE_PAUSE='after-pending-sync',RNX_REMOVE_RELEASE=str(W/'release')),stdout=sp.PIPE,stderr=sp.PIPE)
lines=[];buf=b'';sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ)
try:
    deadline=time.monotonic()+30
    ready=False
    while time.monotonic()<deadline and not ready:
        if not sel.select(.2):assert p.poll() is None,(p.returncode,p.stderr.read());continue
        b=os.read(p.stdout.fileno(),65536);assert b;buf+=b
        while b'\n' in buf:
            raw,buf=buf.split(b'\n',1);v=json.loads(raw);lines.append(v)
            if v.get('paused')=='after-pending-sync':ready=True
    assert ready;assert not entry.exists() and (cache/'removing'/key).is_dir()
    p.kill();p.communicate(timeout=10);assert p.returncode==-signal.SIGKILL
finally:
    if p.poll() is None:p.kill()
    p.wait(timeout=10);sel.close()
command=next(v['resume_command'] for v in lines if v.get('committed'))
assert (m.parent/'.rnx/receipt.json').read_bytes()==before_receipt
t=time.monotonic();r=call(['strace','-f','-qq','-e','trace=execve','-o',O/'old-rebuild.exec',old,'build','--offline','--manifest',m]);(O/'old-rebuild.log').write_text(r.stdout+r.stderr)
seconds=time.monotonic()-t;receipt=json.loads((m.parent/'.rnx/receipt.json').read_text());assert receipt['assembly_key']==key
newartifact=entry/'artifacts'/receipt['executable_blake3'];assert newartifact.stat().st_ino!=old_inode
trace=(O/'old-rebuild.exec').read_text();compiles=[v for v in trace.splitlines() if '--crate-name' in v and 'rustc' in v];assert compiles, 'a ready attachment is not a rebuild'
before=snap(entry);pending_before=snap(cache/'removing'/key);locks_before={n:(m.parent/n).read_bytes() for n in ['rnx.lock','rnx.Cargo.lock']};newreceipt=(m.parent/'.rnx/receipt.json').read_bytes()
# Inspection never resumes automatically and distinguishes the two locations.
v=json.loads(call([T,'cache','list','--root',cache,'--manifest',m]).stdout)
assert [(e['id'],e['location']) for e in v['entries']]==[(key,'entries'),(key,'removing')]
assert v['entries'][0]['referenced_by']==[str(m)] and 'referenced_by' not in v['entries'][1]
assert snap(entry)==before and snap(cache/'removing'/key)==pending_before
r=call(['/bin/sh','-c',command]);assert not (cache/'removing'/key).exists() and snap(entry)==before
assert locks_before==before_locks and all((m.parent/n).read_bytes()==b for n,b in before_locks.items()) and (m.parent/'.rnx/receipt.json').read_bytes()==newreceipt
answer=call([old,'eval','--manifest',m,'--','keep::read()']);assert answer.stdout=='fixture runtime\n'
(O/'rebuild.json').write_text(json.dumps(dict(key=key,old_tool=str(old),old_tool_sha256=sha(old),old_inode=old_inode,new_inode=newartifact.stat().st_ino,compile_execs=len(compiles),build_seconds=seconds,receipt_rebound_to_same_key=True,pending_and_visible_separate=True,new_visible_bytes_and_metadata_unchanged=True,locks_unchanged=True,old_tool_eval=answer.stdout,resume_command=command),indent=2)+'\n')
print('PASS genuine old-tool rebuild and resume preserve the new visible entry',flush=True)
