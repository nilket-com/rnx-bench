#!/usr/bin/env python3
"""Product reader v1/v2 conformance; filesystem semantics, not digest equality."""
import hashlib,json,os,pathlib,shutil,subprocess,tempfile
from vectors import tree as reference_tree,digest as reference_blake
B=pathlib.Path(__file__).resolve().parents[2]; R=B.parent/'rnx'
OUT=B/'results/inventory-encoding-0065';OUT.mkdir(exist_ok=True)
BIN=R/'tools/project/target/release/rnx-project-assembly-probe'
rows=[]
def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE)
def observe(label,mode,path,entries=100000,limit=512*1024*1024,ok=True,word=None):
    values=[]
    for version in ['v1','v2']:
        p=subprocess.run([str(BIN),'fingerprint-'+version,mode,str(path),str(entries),str(limit)],capture_output=True,timeout=5)
        assert (p.returncode==0)==ok,(label,version,p.stderr.decode())
        if ok:
            assert not p.stderr
            v=json.loads(p.stdout);values.append(v)
            fs=v.get('files',[v]);base=path if mode!='one' else path.parent
            for f in fs:
                b=(base/f['path']).read_bytes()
                assert f['bytes']==len(b)
                h=hashlib.sha256(b).hexdigest() if version=='v1' else reference_blake(b)
                assert f['sha256' if version=='v1' else 'blake3']==h
            if mode!='one' and version=='v2':
                fs=[{'path':f['path'],'hex':(base/f['path']).read_bytes().hex(),'executable':f['executable']} for f in fs]
                assert v['blake3']==reference_tree(fs)
        else:
            error=p.stderr.decode();values.append(error)
            assert word is None or word in error,(label,error)
    if ok:
        def shape(v):
            if isinstance(v,list):return [shape(x) for x in v]
            if isinstance(v,dict):return {k:shape(x) for k,x in v.items() if k not in ('sha256','blake3')}
            return v
        assert shape(values[0])==shape(values[1]),label
    else:assert values[0]==values[1],label
    rows.append({'case':label,'mode':mode,'ok':ok,'v1':values[0],'v2':values[1]})
with tempfile.TemporaryDirectory(prefix='rnx-0065-encoding-') as td:
    base=pathlib.Path(td);root=base/'source';root.mkdir()
    observe('empty source','source',root)
    for n in [0,1,16383,16384,16385,32768,32769]:
        (root/'data').write_bytes(bytes(range(256))*(n//256)+bytes(range(n%256)))
        observe(f'file {n}','one',root/'data',limit=n)
        observe(f'tree {n}','source',root,limit=n)
        if n:observe(f'one over allowance {n}','one',root/'data',limit=n-1,ok=False,word='byte allowance')
    observe('entry bound','source',root,entries=0,ok=False,word='entry allowance')
    os.chmod(root/'data',0o700);observe('executable bit','source',root)
    (root/'data').unlink()
    (root/'nested').mkdir();(root/'nested'/'é"🙂').write_bytes(b'a\x00b')
    observe('unicode quotes nested','source',root)
    git(root,'init','--quiet');git(root,'add','.')
    observe('native tracked','native',root)
    (root/'nested'/'é"🙂').write_bytes(b'changed')
    observe('dirty working bytes','native',root)
    (root/'untracked').write_bytes(b'x')
    observe('untracked refuses','native',root,ok=False,word='untracked')
    (root/'untracked').unlink()
    (root/'.gitignore').write_text('ignored\n');git(root,'add','.gitignore');(root/'ignored').write_bytes(b'x')
    observe('ignored excluded','native',root)
    (root/'missing').write_bytes(b'x');git(root,'add','missing');(root/'missing').unlink()
    observe('missing tracked','native',root,ok=False);git(root,'rm','--cached','missing')
    os.symlink('nested',root/'link');observe('symlink directory source','source',root,ok=False,word='symlink')
    git(root,'add','link');observe('symlink in index','native',root,ok=False,word='symlink')
    git(root,'rm','--cached','link');(root/'link').unlink()
    (root/'nested'/'é"🙂').unlink();(root/'nested').rmdir();os.symlink('elsewhere',root/'nested')
    (root/'.gitignore').write_text('ignored\nnested\n')
    observe('symlink component replaces directory','native',root,ok=False,word='symlink')
    (root/'nested').unlink();(root/'nested').mkdir();(root/'nested'/'é"🙂').write_bytes(b'x')
    os.symlink(root,base/'root-link');observe('symlink root','native',base/'root-link',ok=False,word='symlink')
    os.mkfifo(root/'fifo');observe('fifo single','one',root/'fifo',ok=False,word='regular');(root/'fifo').unlink()
    os.close(os.open(os.fsencode(root)+b'/\xff',os.O_CREAT|os.O_WRONLY,0o600))
    observe('non Unicode source','source',root,ok=False,word='non-Unicode')
    os.unlink(os.fsencode(root)+b'/\xff')
    blob=git(root,'hash-object','.gitignore').decode().strip()
    git(root,'update-index','--add','--cacheinfo',f'160000,{blob},child')
    observe('gitlink refuses','native',root,ok=False,word='submodule');git(root,'update-index','--force-remove','child')
    git(root,'update-index','--force-remove','.gitignore')
    cmd=['git','-C',str(root),'update-index','--index-info']
    subprocess.run(cmd,input=f'100644 {blob} 1\t.gitignore\n100644 {blob} 2\t.gitignore\n'.encode(),check=True)
    observe('unmerged index','native',root,ok=False,word='unmerged')
(OUT/'reader-results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
(OUT/'reader-conditions.json').write_text(json.dumps({'binary':str(BIN),'sha256':hashlib.sha256(BIN.read_bytes()).hexdigest(),'cases':len(rows),'timeouts_seconds':5},indent=2)+'\n')
print(len(rows),'paired reader cases pass')
