from common import *
setup=json.loads((O/'real-setup.json').read_text());exe=Path(setup['exe']);p=T/'path-combined';p.mkdir();(p/'main.rn').write_bytes((B/'examples/polars/main.rn').read_bytes())
(p/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath='+json.dumps(setup['checkout'])+'\n')
run([exe,'project','add','--manifest',p/'rnx.toml','polars','postgres'])
for op in ['lock','build']:
 r=run(['taskset','-c','0-15',exe,'project',op,'--offline','--manifest',p/'rnx.toml'],timeout=1800);(O/('path-combined-'+op+'.log')).write_bytes(r.stderr)
out=T/'path-combined-output';out.mkdir();r=run([exe,'project','run','--manifest',p/'rnx.toml','--',out]);assert (out/'tiny.parquet').is_file();run([exe,'project','eval','--manifest',p/'rnx.toml','--','postgres::query'])
lock=json.loads((p/'rnx.lock').read_text());receipt=json.loads((p/'.rnx/receipt.json').read_text());assert lock['format']==3 and receipt['format']==4
save('path-combined.json',{'lock_format':lock['format'],'receipt_format':receipt['format'],'assembly_key':receipt['assembly_key'],'postgres_registration':True,'parquet_bytes':(out/'tiny.parquet').stat().st_size,'stdout':r.stdout.decode()});print('Real combined path assembly and pipeline pass',flush=True)
