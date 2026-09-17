#!/usr/bin/env python3
"""Drive the native-boundary prototype through real rnx scripts and a held session."""
import hashlib,json,os,pathlib,select,subprocess,tempfile,time
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1];OUT=BENCH/'results/polars-boundary-0058';EXE=HERE/'target/release/rnx-polars-boundary'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','POLARS_'))};ENV.update(TERM='xterm',NO_COLOR='1',POLARS_MAX_THREADS='2')
results={}
with tempfile.TemporaryDirectory(prefix='rnx-polars-boundary-') as tmp:
    d=pathlib.Path(tmp);ENV.update(RNX_CONFIG=str(d/'absent'),RNX_HISTORY=str(d/'history'))
    source='''pub fn main(_) {
 let frame=polars::fixture()?; let base=frame.lazy();
 let key=polars::col("k"); let value=polars::col("v"); let one=polars::lit(1);
 let keys=[key]; let aggs=[value.sum().alias("v")];
 let grouped=base.filter(value.gt(one)).group_by(keys)?;
 let plan=grouped.agg(aggs)?;
 let first=plan.collect()?.observed()?; let second=plan.collect()?.observed()?;
 let again=grouped.agg(aggs)?.collect()?.observed()?;
 let orig=frame.observed()?;
 let added=base.group_by(keys)?.agg([(value+one).sum().alias("v")])?.collect()?.observed()?;
 let method=base.group_by(keys)?.agg([value.add(one).sum().alias("v")])?.collect()?.observed()?;
 let bad=base.filter(polars::col("missing").gt(one)).collect();
 println!("{}",json::stringify([first,second,again,orig,added,method,bad.is_err(),base.collect()?.observed()?])?);
 0
}'''
    f=d/'main.rn';f.write_text(source)
    r=subprocess.run([str(EXE),'run',str(f)],env=ENV,capture_output=True,text=True,timeout=60)
    assert r.returncode!=0 and 'can call blocking only when running on the multi-threaded runtime' in r.stderr,(r.stdout,r.stderr)
    results['file_run_stop']={'status':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    traced=subprocess.run([str(EXE),'run',str(f)],env={**ENV,'RUST_BACKTRACE':'1'},capture_output=True,text=True,timeout=60)
    (OUT/'file-run-backtrace.log').write_text(traced.stdout+traced.stderr)
    r=subprocess.run([str(EXE),'eval',source[source.index('{'):]],env=ENV,capture_output=True,text=True,timeout=60)
    assert r.returncode==0,(r.stdout,r.stderr)
    data=json.loads(r.stdout.splitlines()[0]);expected=[['a',2],['🦀',3]]
    assert data[:3]==[expected]*3 and data[3]==[['a',1],['a',2],['🦀',3]] and data[4:6]==[[['a',5],['🦀',4]]]*2 and data[6] is True and data[7]==data[3],data
    results['registration_borrow_reuse_arithmetic_failure_recovery']=data
    cases={'ordinary':'k,v\na,1\n','renamed':'x,y\na,1\n','duplicate':'k,k\na,1\n','deduplicated-spelling':'k,k_duplicated_0\na,1\n','quoted':'"k,part","v\npart"\na,1\n','reordered':'v,k\n1,a\n','short':'k\na\n','extra':'k,v,z\na,1,z\n'}
    csv={}
    for name,text in cases.items():
        path=d/(name+'.csv');path.write_text(text);csv[name]={}
        for mode in ['schema','dtypes','header','raw-header']:
            code='pub fn main(_) { let r=polars::csv('+json.dumps(str(path))+','+json.dumps(mode)+'); let o=match r { Ok(v)=>#{ok:v}, Err(e)=>#{error:e} }; println!("{}",json::stringify(o)?); 0 }'
            f.write_text(code);r=subprocess.run([str(EXE),'eval',code[code.index('{'):]],env=ENV,capture_output=True,text=True,timeout=30)
            assert r.returncode==0,(name,mode,r.stdout,r.stderr)
            csv[name][mode]=json.loads(r.stdout.splitlines()[0])
    assert csv['renamed']['schema']=={'ok':['k','v']}
    assert csv['duplicate']['header']==csv['deduplicated-spelling']['header']
    assert csv['duplicate']['raw-header']=={'ok':['k','k']}
    assert csv['deduplicated-spelling']['raw-header']=={'ok':['k','k_duplicated_0']}
    assert csv['quoted']['raw-header']=={'ok':['k,part','v\npart']}
    assert csv['short']['raw-header']=={'ok':['k']} and csv['extra']['raw-header']=={'ok':['k','v','z']}
    results['csv']=csv
    matrix={}
    for name,expr,entry,ok in [
        ('construct-file','polars::fixture()','run',True),
        ('collect-file','polars::fixture().unwrap().lazy().collect()','run',False),
        ('collect-sync-eval','polars::fixture().unwrap().lazy().collect()','eval',True),
        ('collect-async-eval','{ time::sleep(0).await; polars::fixture().unwrap().lazy().collect() }','eval',False),
    ]:
        f.write_text('pub fn main(_) { '+expr+' }');args=['run',str(f)] if entry=='run' else ['eval',expr]
        r=subprocess.run([str(EXE),*args],env=ENV,capture_output=True,text=True,timeout=30)
        assert (r.returncode==0)==ok,(name,r.stdout,r.stderr)
        if not ok:assert 'can call blocking only when running on the multi-threaded runtime' in r.stderr
        matrix[name]={'status':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    results['runtime_matrix']=matrix
    p=subprocess.Popen([str(EXE),'--no-splash','repl'],env=ENV,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
    pending=b''
    def until(marker):
        global pending
        end=time.monotonic()+30
        while marker not in pending:
            assert time.monotonic()<end,('timeout',pending)
            if select.select([p.stdout],[],[],.1)[0]:
                part=os.read(p.stdout.fileno(),65536);assert part,('eof',p.poll(),pending);pending+=part
        before,pending=pending.split(marker,1);return before.decode()
    def send(line,marker):p.stdin.write((line+'\n').encode());return until(marker.encode())
    def snapshot():
        base=pathlib.Path('/proc',str(p.pid));fds={}
        for fd in (base/'fd').iterdir():
            try:fds[fd.name]=os.readlink(fd)
            except FileNotFoundError:pass
        return {'tasks':len(list((base/'task').iterdir())),'fds':fds}
    try:
        send('"READY"','"READY"');states={'before':snapshot()}
        send('let f=polars::fixture().unwrap(); let q=f.lazy(); "BOUND"','"BOUND"')
        send('let a=q.collect().unwrap(); a.observed().unwrap(); "FIRST"','"FIRST"');states['first']=snapshot();time.sleep(.3);states['idle']=snapshot()
        text=send('q.collect().unwrap().observed().unwrap()','[("a", 1), ("a", 2), ("🦀", 3)]')
        states['second']=snapshot();p.stdin.write(b':reset\n');send('"RESET"','"RESET"');states['reset']=snapshot()
        p.stdin.write(b':q\n');p.stdin.close();p.wait(timeout=15);assert p.returncode==0 and not p.stderr.read()
        states['exited']=not pathlib.Path('/proc',str(p.pid)).exists();results['ownership']=states
    finally:
        if p.poll() is None:p.kill();p.wait()
results['binary_sha256']=hashlib.sha256(EXE.read_bytes()).hexdigest()
(OUT/'results.json').write_text(json.dumps(results,indent=2)+'\n');print('STOP reproduced in file run; PASS synchronous registration, reuse, ADD, CSV observations and idle/reset ownership')
