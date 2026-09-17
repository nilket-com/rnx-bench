#!/usr/bin/env python3
"""0058 gate 3: real native preview, hostile text and ordinary opaque rendering."""
import argparse, hashlib, json, os, pathlib, subprocess, tempfile
import polars as pl
HERE=pathlib.Path(__file__).resolve().parent
ap=argparse.ArgumentParser()
ap.add_argument('--binary',type=pathlib.Path,default=HERE.parents[2]/'rnx/adapters/polars/target/release/rnx-polars')
ap.add_argument('--output',type=pathlib.Path,default=HERE.parents[1]/'results/polars-preview-0058')
a=ap.parse_args();exe=a.binary.resolve();a.output.mkdir(parents=True,exist_ok=True)
env={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','POLARS_'))}
env.update(TERM='xterm',NO_COLOR='1',POLARS_MAX_THREADS='2')
results={}
with tempfile.TemporaryDirectory(prefix='rnx-polars-preview-') as tmp:
    d=pathlib.Path(tmp);env.update(RNX_CONFIG=str(d/'absent'),RNX_HISTORY=str(d/'history'))
    def invoke(args, stdin=None):
        r=subprocess.run([str(exe),*args],env=env,input=stdin,capture_output=True,text=True,timeout=30)
        assert r.returncode==0 and not r.stderr,(r.returncode,r.stdout,r.stderr)
        return r.stdout
    def preview(name,frame):
        path=d/(name+'.parquet');frame.write_parquet(path,compression='uncompressed')
        f=d/'main.rn';f.write_text('pub fn main(_) { let f=polars::read_parquet('+json.dumps(str(path))+')?; let a=f.preview()?; let b=f.preview()?; assert!(a==b); println!("{}",a); }')
        output=invoke(['run',str(f)])
        assert output.endswith('\n');text=output[:-1]
        assert len(text.encode())<=8192
        assert not any(ord(c)<32 and c!='\n' or 127<=ord(c)<160 for c in text)
        (a.output/(name+'.txt')).write_text(text)
        results[name]={'bytes':len(text.encode()),'shape':frame.shape,'sha256':hashlib.sha256(text.encode()).hexdigest()}
        return text,path
    frame=pl.DataFrame({'category':['a','🦀',None,'null','line\nnext','\x1b[2J\t"\\'],'total':[2,7,None,0,-1,8]},schema={'category':pl.String,'total':pl.Int64})
    text,path=preview('specimen',frame)
    assert text.startswith('DataFrame: 6 rows × 2 columns\n')
    assert '"category": string | "total": i64' in text
    assert 'null | null' in text and '"null" | 0' in text and '\\u{1b}[2J\\t' in text
    # Bare native values remain opaque; preview itself writes nothing.
    opaque=invoke(['eval','polars::read_parquet('+json.dumps(str(path))+').unwrap()'])
    assert 'DataFrame' in opaque and 'category' not in opaque and 'line' not in opaque,opaque
    silent=invoke(['eval','{ let f=polars::read_parquet('+json.dumps(str(path))+').unwrap(); let s=f.preview().unwrap(); () }'])
    assert not silent.strip(),silent
    session=invoke([], 'let frame=polars::read_parquet('+json.dumps(str(path))+').unwrap();\nframe\nprintln!("{}",frame.preview().unwrap());\n:quit\n')
    assert 'DataFrame' in session and text in session,session
    assert session.index('DataFrame') < session.index('DataFrame: 6 rows'),session
    results['opaque']={'text':opaque,'preview_no_stream_output':True,'session':session}
    for rows,cols in [(0,1),(9,7),(10,8),(11,9),(100,100)]:
        text,_=preview(f'shape-{rows}-{cols}',pl.DataFrame({f'c{i}':['value']*rows for i in range(cols)},schema={f'c{i}':pl.String for i in range(cols)}))
        assert text.count('"value"')==min(rows,10)*min(cols,8)
        assert ('omitted by display limits' in text)==(rows>10 or cols>8)
    for count in [79,80,81,100000]:
        name='🦀'*count;value='e\u0301'*(count//2)+('🦀' if count%2 else '')
        text,_=preview('scalar-'+str(count),pl.DataFrame({name:[value]},schema={name:pl.String}))
        assert text.count('…[truncated]')==(2 if count>80 else 0)
        assert text.count('🦀')==min(count,80)+(1 if count<80 and count%2 else 0)
    text,_=preview('byte-limit',pl.DataFrame({f'c{i}':['\x1b'*100]*11 for i in range(9)},schema={f'c{i}':pl.String for i in range(9)}))
    assert text.endswith('\n[preview byte limit; remainder omitted]\n')
    assert text.count('\\u{1b}')%80==0
    text,_=preview('integers-bools',pl.DataFrame({'i':[-2**63,2**63-1,None],'b':[True,False,None]},schema={'i':pl.Int64,'b':pl.Boolean}))
    assert '-9223372036854775808 | true' in text and '9223372036854775807 | false' in text and 'null | null' in text
    floats=[-0.0,0.0,5e-324,1.7976931348623157e308,1.2345678901234567,None,float('inf'),float('-inf'),float('nan')]
    text,_=preview('floats',pl.DataFrame({'f':floats},schema={'f':pl.Float64}))
    values=text.splitlines()[2:]
    import struct, math
    for original,spelling in zip(floats,values):
        if original is None: assert spelling=='null'
        elif math.isnan(original): assert math.isnan(float(spelling))
        else: assert struct.pack('d',float(spelling))==struct.pack('d',original),(original,spelling)
    assert all(len(x)<80 for x in values)
results['binary_sha256']=hashlib.sha256(exe.read_bytes()).hexdigest()
(a.output/'results.json').write_text(json.dumps(results,indent=2,ensure_ascii=False)+'\n')
print('PASS: preview dimensions, row/column/scalar/byte limits, escaping, float bits, reuse, silence and opaque values')
