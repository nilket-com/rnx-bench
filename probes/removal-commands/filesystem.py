"""Private, disposable gate-one ownership and filesystem cases; no user stores."""
from pathlib import Path
import os, subprocess as sp, json, hashlib, stat, fcntl, signal, selectors, time, shutil, socket, atexit

H=Path(__file__).resolve().parent; B=H.parents[1]
P=H/'target/bin/rnx-project-support'
W=H/'target/cases'; O=Path(os.environ.get('RNX_REMOVAL_RESULTS',str(B/'results/removal-commands-0066'))).resolve();O.mkdir(parents=True,exist_ok=True)
assert not W.exists(), 'fresh cases directory required'
os.umask(0o077); W.mkdir(parents=True); E={k:v for k,v in os.environ.items() if not k.startswith('RNX_REMOVE_')}
ID='a'*64; OTHER='b'*64; rows=[]
children=[]
def reap():
    for p in children:
        if p.poll() is None:p.kill()
        p.wait(timeout=5)
atexit.register(reap)

def fixture(label,kind='cache'):
    root=W/label; entry=root/'entries'/ID; entry.mkdir(parents=True)
    (entry/'sub').mkdir(); (entry/'sub/data').write_text('fixture bytes')
    (entry/'ready.json').write_text('{"format":999,"owned":"unrecognized data"}')
    if kind=='cache':
        (root/'locks').mkdir(); (root/'locks'/f'{ID}.lock').touch()
    else:
        (root/'install.lock').touch(); (root/'current.json').write_text(json.dumps({'format':2,'id':OTHER}))
    return root,entry

def argv(root,kind='cache',flags=('--quiescent',),program=P):
    return list(map(str,[program,kind,'remove',ID,'--root',root,*flags]))

def snapshot(root):
    result={}
    for base,dirs,files in os.walk(root,followlinks=False):
        for n in dirs+files:
            p=Path(base)/n;s=p.lstat(); data=None
            if stat.S_ISREG(s.st_mode): data=hashlib.sha256(p.read_bytes()).hexdigest()
            elif stat.S_ISLNK(s.st_mode): data=os.readlink(p)
            result[str(p.relative_to(root))]=(s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,data)
    return result

def call(a,ok=True,contains=None,env=None,cwd=None):
    p=sp.run(a,capture_output=True,text=True,env=env or E,cwd=cwd,timeout=15)
    assert (p.returncode==0)==ok,(a,p.returncode,p.stdout,p.stderr)
    if contains: assert contains in p.stdout+p.stderr,(contains,p.stdout,p.stderr)
    return p

def record(label,**details):
    rows.append(dict(case=label,passed=True,**details));print('PASS',label,flush=True)

def refusal(label,mutate=lambda r,e:None,kind='cache',contains=None,env=None):
    r,e=fixture(label,kind); mutate(r,e);before=snapshot(r)
    p=call(argv(r,kind),False,contains,env);assert snapshot(r)==before
    record(label,status=p.returncode,diagnostic=p.stderr.strip())

def paused(r,phase,kind='cache'):
    env=dict(E,RNX_REMOVE_PAUSE=phase,RNX_REMOVE_RELEASE=str(r/'release'))
    p=sp.Popen(argv(r,kind),env=env,stdout=sp.PIPE,stderr=sp.PIPE,text=True)
    children.append(p)
    lines=[];sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ)
    deadline=time.monotonic()+15
    # Read bytes directly: TextIO buffering can hide a second ready line from select.
    buf=b''
    while time.monotonic()<deadline:
        if not sel.select(1):
            assert p.poll() is None,(p.returncode,p.stderr.read());continue
        chunk=os.read(p.stdout.fileno(),65536);assert chunk,(p.poll(),p.stderr.read());buf+=chunk
        while b'\n' in buf:
            line,buf=buf.split(b'\n',1);v=json.loads(line);lines.append(v)
            if v.get('paused')==phase:sel.close();return p,lines
    p.kill();p.wait();raise AssertionError('pause timeout')

def resumed(r,lines,kind='cache'):
    command=next(v['resume_command'] for v in lines if v.get('committed'))
    p=call(['/bin/sh','-c',command]);assert not (r/'removing'/ID).exists()
    return command,p

# Read-only inspection remains read-only even while a writer owns the existing lock.
r,e=fixture('inspection');before=snapshot(r)
with (r/'locks'/f'{ID}.lock').open('r+') as f:
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    call([str(P),'cache','list','--root',str(r)])
    call(argv(r,flags=('--dry-run',)),contains='not reserved')
assert snapshot(r)==before;record('inspection writes nothing and takes no writer lock')
call(argv(r,flags=()),False,'requires --quiescent');assert snapshot(r)==before
record('quiescence required before writes')

for kind in ['cache','runtime']:
    r,e=fixture('busy-'+kind,kind);before=snapshot(r)
    lock=r/('install.lock' if kind=='runtime' else 'locks/'+ID+'.lock')
    with lock.open('r+') as f:
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        call(argv(r,kind),False,'writer lock')
    assert snapshot(r)==before;record('busy '+kind+' writer refuses')

for version in [1,2]:
    refusal('selected-'+str(version),lambda r,e:(r/'current.json').write_text(json.dumps({'format':version,'id':ID})),'runtime','selected runtime')
    r,e=fixture('selected-pending-'+str(version),'runtime');(r/'removing').mkdir();e.rename(r/'removing'/ID)
    (r/'current.json').write_text(json.dumps({'format':version,'id':ID}));before=snapshot(r)
    call(argv(r,'runtime',('--resume','--quiescent')),False,'selected runtime');assert snapshot(r)==before
    record('selected pending runtime format '+str(version))
refusal('invalid-selection',lambda r,e:(r/'current.json').write_text('{'),'runtime','uninterpretable')
refusal('opposite-root',lambda r,e:(r/'install.lock').touch(),contains='opposite')
r,e=fixture('cwd');before=snapshot(r);call(argv(r),False,'working directory',cwd=e);assert snapshot(r)==before;record('cwd inside target')
r,e=fixture('executable');q=e/'probe';shutil.copy2(P,q);before=snapshot(r);call(argv(r,program=q),False,'executable');assert snapshot(r)==before;record('executable inside target')

# Only leaf names are unlinked; no content or shared-file permissions are changed.
r,e=fixture('leaves');outside=W/'outside';outside.mkdir();sent=outside/'sentinel';sent.write_text('keep')
(e/'file-link').symlink_to(sent);(e/'directory-link').symlink_to(outside,target_is_directory=True)
os.link(sent,e/'hardlink');(e/'readonly').write_text('readonly');(e/'readonly').chmod(0o400)
before=sent.stat();lock=(r/'locks'/f'{ID}.lock').stat();call(argv(r));after=sent.stat()
assert sent.read_text()=='keep' and (before.st_ino,before.st_mode,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_mode,after.st_size,after.st_mtime_ns)
assert not e.exists() and (r/'locks'/f'{ID}.lock').stat().st_ino==lock.st_ino
record('symlink leaves hardlink and readonly file',outside_unchanged=True,lock_inode_preserved=True)
refusal('fifo',lambda r,e:os.mkfifo(e/'fifo'),contains='special file')
r,e=fixture('socket');s=socket.socket(socket.AF_UNIX);previous=Path.cwd();os.chdir(e)
try:s.bind('sock')
finally:os.chdir(previous)
before=snapshot(r);call(argv(r),False,'special file');assert snapshot(r)==before;s.close();record('socket refuses without opening')

for control in ['entries','locks','entry','removing','lockfile']:
    r,e=fixture('symlink-'+control)
    target={'entries':r/'entries','locks':r/'locks','entry':e,'removing':r/'removing','lockfile':r/'locks'/f'{ID}.lock'}[control]
    if control=='removing':target.mkdir()
    moved=r/('real-'+control);target.rename(moved);target.symlink_to(moved,target_is_directory=moved.is_dir())
    before=snapshot(r);call(argv(r),False,'openat2');assert snapshot(r)==before;record('control symlink '+control)
r,e=fixture('root-spelling');alias=W/'root-link';alias.symlink_to(r,target_is_directory=True)
call(argv(alias));assert not e.exists();record('user root symlink canonicalized')

for errno in [38,22]:
    refusal('open-error-'+str(errno),contains='no fallback',env=dict(E,RNX_REMOVE_OPEN_ERRNO=str(errno)))
refusal('node-bound',env=dict(E,RNX_REMOVE_NODE_LIMIT='1'),contains='allowance')
r,e=fixture('depth-bound');p=e
for _ in range(130):p=p/'d';p.mkdir()
before=snapshot(r);call(argv(r),False,'depth');assert snapshot(r)==before;record('depth bound before rename')

r,e=fixture('replacement');p,lines=paused(r,'before-rename');old=r/'entries'/OTHER;e.rename(old);e.mkdir();(e/'new').write_text('new identity');before=snapshot(r/'entries');(r/'release').touch();out,err=p.communicate(timeout=15)
assert p.returncode==1 and 'identity changed before commit' in err and snapshot(r/'entries')==before
record('replacement before rename refused')

for sig in [signal.SIGINT,signal.SIGTERM,signal.SIGKILL]:
    for phase in ['before-rename','after-rename','during-delete']:
        label=f'{sig.name}-{phase}';r,e=fixture(label);before=snapshot(e);p,lines=paused(r,phase)
        pending=r/'removing'/ID
        if phase!='before-rename':
            assert not e.exists() and pending.is_dir()
            listed=json.loads(call([str(P),'cache','list','--root',str(r)]).stdout)
            assert [(v['id'],v['location']) for v in listed['entries']]==[(ID,'removing')]
        p.send_signal(sig);out,err=p.communicate(timeout=15)
        assert p.returncode==(-9 if sig==signal.SIGKILL else 128+sig),(p.returncode,err)
        if phase=='before-rename':assert snapshot(e)==before
        else:
            assert pending.exists() and not e.exists()
            if phase=='after-rename':assert snapshot(pending)==before
            if sig!=signal.SIGKILL:assert '--resume --quiescent' in err
            # A new visible entry is distinct; resume must not touch it.
            e.mkdir();(e/'rebuilt').write_text('new visible fixture');visible=snapshot(e)
            command,_=resumed(r,lines);assert snapshot(e)==visible
            call(argv(r,flags=('--resume','--quiescent')),False)
        record(label,status=p.returncode,visible_preserved=True)

r,e=fixture("resume ' quoted path");p,lines=paused(r,'after-rename');p.kill();p.communicate(timeout=15)
before=snapshot(r);call(argv(r),False,'pending removal exists');assert snapshot(r)==before
command,_=resumed(r,lines);assert "'\\''" in command
record('pending refuses normal removal; quoted resume command executes')

# The actual syscall topology: st_dev alone cannot see the directory or file bind.
mount_rows=[]
for shape in ['bind-subdir','tmpfs-subdir','bind-entry','bind-entries','bind-locks','bind-file']:
    r,e=fixture('mount-'+shape);x=W/('external-'+shape);x.mkdir();(x/'sentinel').write_text('outside')
    (e/'mnt').mkdir();(e/'leaf').write_text('leaf')
    if shape=='bind-subdir':src,dst=x,e/'mnt';mount=['--bind',src,dst]
    elif shape=='tmpfs-subdir':src,dst=x,e/'mnt';mount=['--tmpfs',dst]
    elif shape=='bind-entry':src,dst=e,e;mount=['--bind',src,dst]
    elif shape=='bind-entries':src,dst=r/'entries',r/'entries';mount=['--bind',src,dst]
    elif shape=='bind-locks':src,dst=r/'locks',r/'locks';mount=['--bind',src,dst]
    else:src,dst=x/'sentinel',e/'leaf';mount=['--bind',src,dst]
    before=snapshot(r);outside_before=snapshot(x)
    script='''import os,sys,json,subprocess as s
p=s.run(sys.argv[3:],capture_output=True,text=True)
print(json.dumps(dict(uid=os.getuid(),entry_device=os.stat(sys.argv[1]).st_dev,mount_device=os.stat(sys.argv[2]).st_dev,status=p.returncode,stdout=p.stdout,stderr=p.stderr,mountinfo=[v for v in open('/proc/self/mountinfo').read().splitlines() if sys.argv[2] in v])))
'''
    a=['bwrap','--unshare-user','--uid',str(os.getuid()),'--gid',str(os.getgid()),'--bind','/','/','--dev','/dev','--proc','/proc',*map(str,mount),'--','python3','-c',script,str(e),str(dst),*argv(r)]
    result=json.loads(call(a).stdout);assert result['status']==1 and 'Invalid cross-device link' in result['stderr'],result
    if shape=='tmpfs-subdir':assert result['entry_device']!=result['mount_device']
    else:assert result['entry_device']==result['mount_device']
    assert snapshot(r)==before and snapshot(x)==outside_before and e.exists()
    mount_rows.append(dict(shape=shape,**result));record(shape+' refused before rename',outside_unchanged=True)

(O/'matrix.json').write_text(json.dumps(dict(cases=rows,mounts=mount_rows,scope='isolated candidate; synthetic control documents; actual syscalls and mounts'),indent=2)+'\n')
trace=O/'inspection-process.trace'
p=call(['strace','-f','-e','trace=process','-o',str(trace),str(P),'cache','list','--root',str(W/'inspection')])
raw=trace.read_text();assert raw.count('execve(')==1 and not any(v in raw for v in ['clone(','clone3(','fork('])
(O/'inspection-process.json').write_text(json.dumps(dict(no_children=True,execs=1,output=json.loads(p.stdout)),indent=2)+'\n')
print('PASS',len(rows),'ownership and filesystem cases',flush=True)
