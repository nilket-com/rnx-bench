from pathlib import Path
import os,json,subprocess as sp,hashlib,stat,selectors,time,signal,atexit,shutil
H=Path('/home/me/work/rnx-bench/probes/removal-final/target/removal-contracts');B=Path('/home/me/work/rnx-bench');R=B.parent/'rnx'
T=Path('/home/me/work/rnx-bench/probes/removal-final/target/tool-support');W=H/'target/contracts';O=B/'results/removal-final-0066/removal-contracts'
assert not W.exists();os.umask(0o077);W.mkdir(parents=True)
E={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','XDG_','GIT_'))};E['HOME']=str(W/'home')
ID='a'*64;OTHER='b'*64;rows=[];children=[]
def finish():
    for p in children:
        if p.poll() is None:p.kill()
        p.wait(timeout=10)
atexit.register(finish)
def snap(root):
    out={}
    for base,ds,fs in os.walk(root,followlinks=False):
        for n in ds+fs:
            p=Path(base)/n;m=p.lstat();content=hashlib.sha256(p.read_bytes()).hexdigest() if stat.S_ISREG(m.st_mode) else os.readlink(p) if stat.S_ISLNK(m.st_mode) else None
            out[str(p.relative_to(root))]=(m.st_ino,m.st_mode,m.st_size,m.st_mtime_ns,content)
    return out
def call(args,ok=True,contains=None,env=None):
    p=sp.run(list(map(str,[T,*args])),env=env or E,capture_output=True,text=True,timeout=20)
    assert (p.returncode==0)==ok,(args,p.returncode,p.stdout,p.stderr)
    if contains:assert contains in p.stdout+p.stderr,(contains,p.stdout,p.stderr)
    return p
def row(n,**v):rows.append(dict(case=n,passed=True,**v));print('PASS',n,flush=True)
def root(n,kind='cache'):
    r=W/n;e=r/'entries'/ID;e.mkdir(parents=True);(e/'data').write_text('old data')
    if kind=='cache':(r/'locks').mkdir();(r/'locks'/f'{ID}.lock').touch()
    else:(r/'install.lock').touch();(r/'current.json').write_text(json.dumps({'format':2,'id':OTHER}))
    return r,e
def remove(r,*flags,kind='cache'):return [kind,'remove',ID,'--root',r,*flags]
def pause(args,phase,r):
    p=sp.Popen(list(map(str,[T,*args])),env=dict(E,RNX_REMOVE_PAUSE=phase,RNX_REMOVE_RELEASE=str(r/'release')),stdout=sp.PIPE,stderr=sp.PIPE);children.append(p)
    sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ);buf=b'';lines=[];end=time.monotonic()+20
    while time.monotonic()<end:
        if not sel.select(.2):assert p.poll() is None,(p.returncode,p.stderr.read());continue
        b=os.read(p.stdout.fileno(),65536);assert b;buf+=b
        while b'\n' in buf:
            line,buf=buf.split(b'\n',1);v=json.loads(line);lines.append(v)
            if v.get('paused')==phase:sel.close();return p,lines
    raise AssertionError('pause timed out')

r,e=root('parse');before=snap(r)
for args in [['cache','list','--all'],['cache','remove','abc','--root',r,'--quiescent'],['cache','remove','A'*64,'--root',r,'--quiescent'],['cache','remove',ID,OTHER,'--root',r,'--quiescent'],['cache','list','--root',r,'--root',r],['cache','list','--dry-run','--root',r],remove(r,'--manifest','x','--quiescent'),['cache','list','--manifest'],['cache','list','--root','relative']]:call(args,False)
assert snap(r)==before;row('exact CLI refuses before writes')
missing=W/'absent/nested';p=call(['cache','list','--root',missing]);assert json.loads(p.stdout)['absent'] and not (W/'absent').exists();row('missing root lists absent without creation')
for label,env,want in [('cache override',dict(E,RNX_PROJECT_CACHE=str(r)),r),('cache xdg',dict(E,XDG_CACHE_HOME=str(W/'xdg')),W/'xdg/rnx/assemblies'),('cache home',E,W/'home/.cache/rnx/assemblies')]:
    p=call(['cache','list'],env=env);assert json.loads(p.stdout)['root']==str(want);row(label)
for label,env,want in [('runtime xdg',dict(E,XDG_DATA_HOME=str(W/'data')),W/'data/rnx/runtimes'),('runtime home',E,W/'home/.local/share/rnx/runtimes')]:
    p=call(['runtime','list'],env=env);assert json.loads(p.stdout)['root']==str(want);row(label)
call(['cache','list'],False,'absolute',dict(E,RNX_PROJECT_CACHE='relative',XDG_CACHE_HOME=str(r)))
call(['cache','list','--root',r],env=dict(E,RNX_PROJECT_CACHE='relative'));row('explicit root wins; invalid environment never falls back')
link=W/'broken';link.symlink_to(W/'never');call(['cache','list','--root',link],False,'broken');row('broken root is not absent')
(r/'entries'/OTHER).mkdir();(r/'entries'/OTHER/'ready.json').write_text('{');(r/'unknown\n\u202ename').touch()
v=json.loads(call(['cache','list','--root',r]).stdout);assert [x['id'] for x in v['entries']]==[ID,OTHER] and v['unknown'] and all(x['metadata']['status']=='unrecognized' for x in v['entries']);row('sorted entries; corrupt and missing metadata; escaped unknown names')
for env,msg in [(dict(E,RNX_REMOVE_ENTRY_LIMIT='1'),'entry allowance'),(dict(E,RNX_REMOVE_OUTPUT_LIMIT='8'),'output'),(dict(E,RNX_REMOVE_MEMORY_LIMIT='10'),'allowance')]:
    before=snap(r);call(['cache','list','--root',r],False,msg,env);assert snap(r)==before
row('entry memory and output bounds refuse without writes')
(e/'ready.json').write_text('{"format":2,"key":"'+ID+'"}');v=json.loads(call(['cache','list','--root',r]).stdout);assert v['entries'][0]['metadata']['status']=='unrecognized';row('known but incomplete entry document is unrecognized')

# Real old/current documents as templates. No source or artifact is validated by annotation.
old=Path('/home/me/work/rnx-bench/probes/removal-commands/templates/old');new=Path('/home/me/work/rnx-bench/probes/removal-commands/templates/new')
def project(name,version=3,kind='shared',cache=None):
    base=W/name;base.mkdir();(base/'.rnx').mkdir();source=old if version==2 else new
    m=base/'rnx.toml';m.write_bytes((source/'rnx.toml').read_bytes());l=json.loads((source/'rnx.lock').read_text());c=json.loads((source/'.rnx/receipt.json').read_text())
    if kind=='shared':
        i=json.loads(l['assembly']['identity']);i['context']['cache_root']=str(cache or r);l['assembly']['identity']=json.dumps(i);c['assembly_key']=ID
    else:
        c.pop('assembly_key',None)
        if version==2:l['format']=1;c['format']=2
        if kind=='executable':
            l['assembly']={'kind':'executable','path':str(W/'override'),('sha256' if version==2 else 'blake3'):'c'*64}
            l['declarations'].pop('runtime',None);l['declarations']['native']={};l['declarations']['executable']={'path':str(W/'override')}
        else:
            l['assembly']={'kind':'generated','target':'x86_64-unknown-linux-gnu','profile':'release','features':[],'rustc':'observed','cargo':'observed'}
            for field in ['manifest','main','cargo_lock']:l['assembly'][field+('_sha256' if version==2 else '_blake3')]='d'*64
    (base/'rnx.lock').write_text(json.dumps(l));(base/'.rnx/receipt.json').write_text(json.dumps(c));return m,l,c
for version in [2,3]:
    m,l,c=project('shared-'+str(version),version);before=snap(m.parent);v=json.loads(call(['cache','list','--root',r,'--manifest',m,'--manifest',m]).stdout)
    assert len(v['references'])==1 and v['entries'][0]['referenced_by']==[str(m)] and snap(m.parent)==before;row('old/current shared reference '+str(version))
    v=json.loads(call(remove(r,'--dry-run','--manifest',m)).stdout);assert v['entries'][0]['referenced_by']==[str(m)];row('annotated dry run '+str(version))
for version in [2,3]:
    for kind in ['generated','executable']:
        m,_,_=project(kind+str(version),version,kind);before=snap(m.parent);v=json.loads(call(['cache','list','--root',r,'--manifest',m]).stdout)
        assert 'referenced_by' not in v['entries'][0] and v['references'][0]['kind']!='shared assembly' and snap(m.parent)==before;row('no digest-only shared match '+kind+str(version))
m,l,c=project('outside',cache=W/'outside');v=json.loads(call(['cache','list','--root',r,'--manifest',m]).stdout);assert v['references'][0]['relation']=='outside selected store';row('reference outside selected store')
m,l,c=project('missing-reference');c['assembly_key']='c'*64;(m.parent/'.rnx/receipt.json').write_text(json.dumps(c));v=json.loads(call(['cache','list','--root',r,'--manifest',m]).stdout);assert v['references'][0]['relation']=='recorded entry missing';row('missing recorded entry')
rp,ep=root('runtime-annotations','runtime');m,l,c=project('runtime-project')
for package in l['inputs']['native']['packages']:
    if package['name']=='rnx':package['root']=str(ep/'source')
(m.parent/'rnx.lock').write_text(json.dumps(l));v=json.loads(call(['runtime','list','--root',rp,'--manifest',m]).stdout);assert v['entries'][0]['referenced_by']==[str(m)];row('runtime reference uses recorded source, not selection or provenance')
pr,pe=root('pending-reference');m,l,c=project('pending-project',cache=pr);(pr/'removing').mkdir();pe.rename(pr/'removing'/ID)
v=json.loads(call(['cache','list','--root',pr,'--manifest',m]).stdout);assert 'referenced_by' not in v['entries'][0] and v['references'][0]['relation']=='recorded entry missing';row('visible reference does not become pending reference')

for label,mutate in [('missing receipt',lambda m,l,c:(m.parent/'.rnx/receipt.json').unlink()),('malformed lock',lambda m,l,c:(m.parent/'rnx.lock').write_text('{')),('unsupported lock',lambda m,l,c:(m.parent/'rnx.lock').write_text(json.dumps(dict(l,format=99)))),('bad key',lambda m,l,c:(m.parent/'.rnx/receipt.json').write_text(json.dumps(dict(c,assembly_key='short')))),('duplicate field',lambda m,l,c:(m.parent/'rnx.lock').write_text('{"format":3,"format":3}')),('oversized manifest',lambda m,l,c:m.write_text(' '*1048577))]:
    m,l,c=project(label.replace(' ','-'));mutate(m,l,c);before=snap(m.parent);p=call(['cache','list','--root',r,'--manifest',m],False,'indeterminate');assert snap(m.parent)==before and json.loads(p.stdout)['references'][0]['status']=='indeterminate';row(label+' is indeterminate')
m,l,c=project('many-paths');call(['cache','list','--root',r,*sum((['--manifest',m] for _ in range(64)),[])])
call(['cache','list','--root',r,*sum((['--manifest',m] for _ in range(65)),[])],False,'64');row('64 supplied paths coalesce; 65 refuse')
empty=W/'unbuilt';empty.mkdir();(empty/'rnx.toml').write_bytes(m.read_bytes());call(['cache','list','--root',r,'--manifest',empty/'rnx.toml'],False,'indeterminate');assert not (empty/'.rnx').exists();row('unbuilt project is not opened for mutation')
for mode in ['edit','replace']:
    m,l,c=project('changed-'+mode);args=['cache','list','--root',r,'--manifest',m];p,lines=pause(args,'annotation-before-recheck',m.parent)
    f=m.parent/'rnx.lock'
    if mode=='edit':f.write_text(f.read_text()+' ')
    else:tmp=f.with_suffix('.new');tmp.write_bytes(f.read_bytes());tmp.replace(f)
    (m.parent/'release').touch();out,err=p.communicate(timeout=20);assert p.returncode==1 and b'changed' in out and b'indeterminate' in err;row('observable annotation '+mode)

# Both parent syncs have distinct pause and failure boundaries.
for phase in ['before-rename','before-root-sync','after-root-sync','before-entries-sync','after-entries-sync','before-pending-sync','after-pending-sync','before-unlink','before-final-sync','after-final-sync']:
    rr,ee=root('failure-'+phase);before=snap(ee);p=call(remove(rr,'--quiescent'),False,'injected',dict(E,RNX_REMOVE_FAIL=phase))
    if phase in ['before-rename','before-root-sync','after-root-sync']:assert snap(ee)==before
    else:
        assert not ee.exists() and '--resume --quiescent' in p.stderr
        if (rr/'removing'/ID).exists():call(remove(rr,'--resume','--quiescent'))
    row('failure boundary '+phase)
for phase in ['before-entries-sync','after-entries-sync','before-pending-sync','after-pending-sync']:
    rr,ee=root('kill-'+phase);p,lines=pause(remove(rr,'--quiescent'),phase,rr)
    # Observe CLOEXEC on the actual product lock descriptor while held.
    lock=rr/'locks'/f'{ID}.lock';fds=[f for f in Path('/proc',str(p.pid),'fd').iterdir() if os.readlink(f)==str(lock)];assert len(fds)==1
    info=Path('/proc',str(p.pid),'fdinfo',fds[0].name).read_text();flags=int(next(v.split()[1] for v in info.splitlines() if v.startswith('flags:')),8);assert flags&os.O_CLOEXEC
    p.kill();p.communicate(timeout=20);assert p.returncode==-9 and not ee.exists();call(remove(rr,'--resume','--quiescent'));row('kill and CLOEXEC '+phase)
rr,ee=root('permission-after');(ee/'locked').mkdir();(ee/'locked/data').write_text('x');(ee/'locked').chmod(0o500)
call(remove(rr,'--quiescent'),False,'Permission denied');assert not ee.exists();(rr/'removing'/ID/'locked').chmod(0o700);call(remove(rr,'--resume','--quiescent'));row('real deletion permission error leaves resumable pending')
rr,ee=root('permission-before');(rr/'entries').chmod(0o500);before=snap(ee);call(remove(rr,'--quiescent'),False,'Permission denied');assert snap(ee)==before;(rr/'entries').chmod(0o700);row('real rename permission error preserves visible entry')

# Relative and symlink spellings coalesce to the explicitly named manifest.
m,l,c=project('relative-project');alias=W/'manifest-link';alias.symlink_to(m)
v=json.loads(call(['cache','list','--root',r,'--manifest',os.path.relpath(m),'--manifest',alias]).stdout)
assert len(v['references'])==1 and v['entries'][0]['referenced_by']==[str(m)];row('relative and symlink manifest spellings coalesce')
# Ordinary binary ignores all injected removal hooks.
rr,ee=root('ordinary');ordinary=Path('/home/me/work/rnx-bench/probes/removal-final/target/tool-ordinary')
p=sp.run(list(map(str,[ordinary,*remove(rr,'--quiescent')])),env=dict(E,RNX_REMOVE_OPEN_ERRNO='38',RNX_REMOVE_PAUSE='before-rename',RNX_REMOVE_FAIL='before-rename',RNX_REMOVE_NODE_LIMIT='1'),capture_output=True,text=True,timeout=20)
assert p.returncode==0 and not ee.exists() and 'paused' not in p.stdout,(p.stdout,p.stderr);row('ordinary product ignores test hooks')

(O/'contracts.json').write_text(json.dumps(dict(cases=rows,count=len(rows)),indent=2)+'\n');print('PASS',len(rows),'contract groups')
