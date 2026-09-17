#!/usr/bin/env python3
"""0058 gate 2: real scripts, independently checked rows and cross-read Parquet."""
import argparse, hashlib, json, os, pathlib, subprocess, tempfile
import polars as pl
HERE = pathlib.Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('--binary', type=pathlib.Path, default=HERE.parents[2]/'rnx/adapters/polars/target/release/rnx-polars')
ap.add_argument('--output', type=pathlib.Path, default=HERE.parents[1]/'results/polars-contract-0058')
args = ap.parse_args(); exe = args.binary.resolve()
env = {k:v for k,v in os.environ.items() if not k.startswith(('RNX_', 'POLARS_'))}
env.update(TERM='xterm', NO_COLOR='1', POLARS_MAX_THREADS='2')
results = {}
def q(s): return json.dumps(str(s), ensure_ascii=False)
with tempfile.TemporaryDirectory(prefix='rnx-polars-contract-') as tmp:
    d = pathlib.Path(tmp); env.update(RNX_CONFIG=str(d/'absent'), RNX_HISTORY=str(d/'history'))
    def run(body):
        source=d/'main.rn'; source.write_text('pub fn main(_) { '+body+'; 0 }')
        p=subprocess.run([str(exe),'run',str(source)],env=env,capture_output=True,text=True,timeout=30)
        assert p.returncode==0 and not p.stderr, (body,p.stdout,p.stderr,p.returncode)
        return json.loads(p.stdout.splitlines()[0]) if p.stdout else None
    def outcome(expr):
        return run('let result='+expr+'; let answer=match result {Ok(_)=>#{ok:true},Err(e)=>#{error:e}}; println!("{}",json::stringify(answer)?)')
    schema='[("k","string"),("v","i64")]'
    path=d/'input.csv'; path.write_text('k,v\na,1\na,2\n🦀,3\n🦀,4\nnull,\n')
    out=d/'answer.parquet'; again=d/'again.parquet'; original=d/'original.parquet'
    run(f'''let path={q(path)}; let schema={schema};
    let frame=polars::read_csv(path,schema)?;
    let second=polars::read_csv(path,schema)?;
    let base=frame.lazy(); let k=polars::col("k"); let v=polars::col("v"); let one=polars::lit(1)?;
    let keys=[k]; let sums=[v.sum().alias("total")]; let order=["k"];
    let grouped=base.filter(v.gt(one)).group_by(keys)?;
    let plan=grouped.agg(sums)?.sort(order)?;
    let result=plan.collect()?; result.write_parquet_new({q(out)})?;
    let bad=base.filter(polars::col("missing").gt(one)).collect(); assert!(bad.is_err());
    let bad_write=result.write_parquet_new({q(out)}); assert!(bad_write.is_err());
    grouped.agg(sums)?.sort(order)?.collect()?.write_parquet_new({q(again)})?;
    frame.write_parquet_new({q(original)})?;
    second.lazy().group_by(keys)?.agg([(v+one).sum().alias("total")])?.collect()?;
    assert!(path=={q(path)}); assert!(schema.len()==2);
    println!("{{}}",json::stringify([bad.is_err(),bad_write.is_err()])?)''')
    expected=pl.DataFrame({'k':['a','🦀'],'total':[2,7]},schema={'k':pl.String,'total':pl.Int64})
    assert pl.read_parquet(out).equals(expected)
    assert pl.read_parquet(again).equals(expected)
    assert pl.read_parquet(original).to_dict(as_series=False)=={'k':['a','a','🦀','🦀','null'],'v':[1,2,3,4,None]}
    python_out=d/'python.parquet'; expected.write_parquet(python_out,compression='uncompressed')
    cross=d/'cross.parquet'
    run(f'let p={q(python_out)}; let f=polars::read_parquet(p)?; polars::read_parquet(p)?; f.write_parquet_new({q(cross)})?')
    assert pl.read_parquet(cross).equals(expected)
    results['pipeline']={'expected':expected.to_dict(as_series=False),'cross_read':True,'reused_after_success_and_failure':True}
    cases={
      'crlf':('k,v\r\na,1\r\n', [['a',1]]),
      'quoted-comma':('k,v\n"a,b",2\n',[['a,b',2]]),
      'quoted-newline':('k,v\n"a\nb",2\n',[['a\nb',2]]),
      'quoted-quote':('k,v\n"a""b",2\n',[['a"b',2]]),
      'short-row':('k,v\na\n',[['a',None]]),
      'empty-fields':('k,v\n,\n',[[None,None]]),
      'quoted-empty':('k,v\n"",1\n',[['',1]]),
      'header-only':('k,v\n',[]),
      'extra-field':('k,v\na,1,z\n',None),
      'bad-int':('k,v\na,no\n',None),
      'duplicate-header':('k,k\na,1\n',None),
      'renamed-header':('x,v\na,1\n',None),
      'reordered-header':('v,k\n1,a\n',None),
      'short-header':('k\na\n',None),
      'extra-header':('k,v,z\na,1,z\n',None),
      'empty-file':('',None),
    }
    csv_results={}
    for name,(text,rows) in cases.items():
        src=d/(name+'.csv'); src.write_bytes(text.encode()); target=d/(name+'.parquet')
        result=outcome(f'polars::read_csv({q(src)},{schema})')
        if rows is None: assert 'error' in result, (name,result)
        else:
            assert result=={'ok':True}, (name,result)
            run(f'polars::read_csv({q(src)},{schema})?.write_parquet_new({q(target)})?')
            actual=[list(row) for row in pl.read_parquet(target).rows()]; assert actual==rows,(name,actual,rows)
            py=pl.read_csv(src,schema={'k':pl.String,'v':pl.Int64})
            assert [list(row) for row in py.rows()]==rows,(name,py)
            result['rows']=actual
        csv_results[name]=result
    results['csv']=csv_results
    # Explicit schema supports all four types and nulls; Parquet retains them.
    allcsv=d/'types.csv'; allcsv.write_text('s,i,f,b\n🦀,-9,1.25,true\nnull,0,-0.0,false\n,,,\n')
    typed=d/'types.parquet'
    run(f'polars::read_csv({q(allcsv)},[("s","string"),("i","i64"),("f","f64"),("b","bool")])?.write_parquet_new({q(typed)})?')
    frame=pl.read_parquet(typed)
    assert frame.schema=={'s':pl.String,'i':pl.Int64,'f':pl.Float64,'b':pl.Boolean}
    assert frame.rows()==[('🦀',-9,1.25,True),('null',0,-0.0,False),(None,None,None,None)]
    results['types']=frame.to_dict(as_series=False)
    errors={}
    for name,invalid in {'empty':'[]','duplicate':'[("k","string"),("k","i64")]','empty-name':'[("","i64")]','dtype':'[("k","date")]','not-vector':'42','not-tuple':'[1]','arity':'[("k",)]','bad-name':'[(1,"i64")]','bad-dtype':'[("k",1)]'}.items():
        result=outcome(f'polars::read_csv({q(d/"does-not-exist")},{invalid})')
        assert 'error' in result and 'polars read_csv:' in result['error'],(name,result)
        errors['schema-'+name]=result
    for name,literal in [('unit','()'),('vector','[]'),('infinity','1.0/0.0')]:
        result=outcome('polars::lit('+literal+')'); assert 'error' in result; errors['lit-'+name]=result
    invalid_utf=d/'invalid.csv';invalid_utf.write_bytes(b'k,v\n\xff,1\n')
    malformed=d/'bad.parquet';malformed.write_bytes(b'not parquet')
    fifo=d/'fifo';os.mkfifo(fifo)
    for name,expr in [
        ('utf8',f'polars::read_csv({q(invalid_utf)},{schema})'),
        ('missing',f'polars::read_csv({q(d/"absent")},{schema})'),
        ('directory',f'polars::read_parquet({q(d)})'),
        ('fifo',f'polars::read_csv({q(fifo)},{schema})'),
        ('malformed-parquet',f'polars::read_parquet({q(malformed)})'),
        ('missing-output-parent',f'polars::read_parquet({q(out)})?.write_parquet_new({q(d/"absent/out")})'),
        ('missing-column',f'polars::read_parquet({q(out)})?.lazy().sort(["missing"])?.collect()')]:
        result=outcome(expr);assert 'error' in result,(name,result);errors[name]=result
    for name,dtype in [('i32',pl.Int32),('u64',pl.UInt64),('date',pl.Date),('null',pl.Null)]:
        unsupported=d/(name+'.parquet');pl.DataFrame({'unsupported':pl.Series([None],dtype=dtype)}).write_parquet(unsupported)
        result=outcome(f'polars::read_parquet({q(unsupported)})');assert 'unsupported column' in result['error'];errors[name]=result
    empty=d/'empty.parquet'
    run(f'polars::read_csv({q(path)},{schema})?.lazy().filter(polars::col("v").gt(polars::lit(99)?)).collect()?.write_parquet_new({q(empty)})?')
    assert pl.read_parquet(empty).height==0
    link=d/'symlink.csv';link.symlink_to(path)
    assert outcome(f'polars::read_csv({q(link)},{schema})')=={'ok':True}
    # Read permission refusal is tested as the ordinary unprivileged fixture user.
    unreadable=d/'unreadable.csv';unreadable.write_text('k,v\na,1\n');unreadable.chmod(0)
    try:
        result=outcome(f'polars::read_csv({q(unreadable)},{schema})')
        assert 'error' in result and 'Permission denied' in result['error'],result
        errors['unreadable']=result
    finally: unreadable.chmod(0o600)
    # Literal bindings survive conversion; malformed arrays are catchable before collect.
    run('let s="hi"; polars::lit(s)?; polars::lit(s)?; assert!(s=="hi"); polars::lit(true)?; polars::lit(1.25)?')
    for name,expr in [
        ('bad-keys',f'polars::read_parquet({q(out)})?.lazy().group_by([1])'),
        ('bad-aggregates',f'polars::read_parquet({q(out)})?.lazy().group_by([polars::col("k")])?.agg([1])'),
        ('bad-sort',f'polars::read_parquet({q(out)})?.lazy().sort([1])'),
        ('not-vector',f'polars::read_parquet({q(out)})?.lazy().group_by(42)'),
        ('unsupported-collected',f'polars::read_parquet({q(typed)})?.lazy().group_by([polars::col("s")])?.agg([polars::col("b").sum()])?.collect()'),
    ]:
        result=outcome(expr);assert 'error' in result;errors[name]=result
    results['refusals']=errors
    results['empty_result_and_symlink']=True
args.output.mkdir(parents=True,exist_ok=True)
results['conditions']={'binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'python_polars':pl.__version__,'threads':2,'engine_provenance':'different revisions, as gate 1 recorded'}
(args.output/'results.json').write_text(json.dumps(results,indent=2,ensure_ascii=False)+'\n')
print('PASS: pipeline, cross-read, 16 CSV cases, types, reuse, empty result, symlink and',len(results['refusals']),'refusals')
