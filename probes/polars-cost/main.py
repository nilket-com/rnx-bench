import json, os, stat, sys
import polars as pl

def preview(frame):
    # The same tiny, supported result and deterministic textual layout as Rune.
    names={'category':'string','total':'i64'}
    lines=[f'DataFrame: {frame.height} rows × {frame.width} columns',
           ' | '.join(json.dumps(c,ensure_ascii=False)+': '+names[c] for c in frame.columns)]
    for row in frame.iter_rows():
        lines.append(' | '.join('null' if v is None else json.dumps(v,ensure_ascii=False) for v in row))
    return '\n'.join(lines)+'\n'

def main():
    if sys.argv[1]=='init':
        pl.lit(1)
        print('ready')
        return
    csv=os.path.join(sys.argv[2],'tiny.csv');parquet=os.path.join(sys.argv[2],'tiny.parquet')
    with open(csv,'x',encoding='utf8',newline='') as f:
        f.write('category,value\na,1\na,2\n🦀,3\n🦀,4\nmissing,\n')
    with open(csv,'rb') as f:
        assert stat.S_ISREG(os.fstat(f.fileno()).st_mode)
        header=pl.read_csv(f,has_header=False,infer_schema=False,n_rows=1)
        assert header.shape==(1,2) and header.row(0)==('category','value')
        f.seek(0)
        frame=pl.read_csv(f,schema={'category':pl.String,'value':pl.Int64})
    plan=frame.lazy().filter(pl.col('value').gt(pl.lit(1))).group_by(pl.col('category')).agg(pl.col('value').sum().alias('total')).sort('category',nulls_last=False)
    result=plan.collect()
    with open(parquet,'xb') as f:
        result.write_parquet(f,compression='uncompressed',row_group_size=512*512)
        f.flush()
    with open(parquet,'rb') as f:
        assert stat.S_ISREG(os.fstat(f.fileno()).st_mode)
        roundtrip=pl.read_parquet(f)
    assert preview(result)==preview(roundtrip)
    assert preview(plan.collect())==preview(result)
    print(preview(roundtrip))
main()
