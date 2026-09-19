from common import *
setup=json.loads((O/'real-setup.json').read_text());exe=Path(setup['exe'])
p=project('real-combined',setup['url'],setup['rev'],['polars','postgres'])
for op in ['lock','build']:
 r=run(['taskset','-c','0-15',exe,'project',op,'--offline','--manifest',p/'rnx.toml'],timeout=1800);(O/('combined-'+op+'.log')).write_bytes(r.stderr)
lock=json.loads((p/'rnx.lock').read_text());identity=json.loads(lock['assembly']['identity']);assert {'rnx','rnx-polars','rnx-postgres'}<=set(g['name'] for g in lock['git'])
out=T/'combined-output';out.mkdir();run([exe,'project','eval','--manifest',p/'rnx.toml','--','postgres::query'])
# Run the shipped one-screen pipeline through the actual project run mode.
(p/'main.rn').write_bytes((B/'examples/polars/main.rn').read_bytes());run([exe,'project','lock','--offline','--manifest',p/'rnx.toml']);run([exe,'project','build','--offline','--manifest',p/'rnx.toml']);r=run([exe,'project','run','--manifest',p/'rnx.toml','--',out]);(O/'combined-pipeline.stdout').write_bytes(r.stdout);assert (out/'tiny.parquet').is_file()
save('combined.json',{'git_packages':lock['git'],'identity':lock['assembly']['identity'],'parquet_bytes':(out/'tiny.parquet').stat().st_size,'postgres_registration':True,'scope':'real combined build and Polars round-trip; database transaction journeys remain gate 4'})
print('Real combined Git assembly and pipeline pass',flush=True)
