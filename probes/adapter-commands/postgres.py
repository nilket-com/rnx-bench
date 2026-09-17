"""Catalogue PostgreSQL lifecycle registration, executed together with Polars."""
from common import *
import shutil,tomllib
sys.path.insert(0,str(B/'probes/postgres'))
from cluster import Cluster
app=W/'combined';app.mkdir()
base='format=1\n[application]\nentry="main.rn"\n[runtime]\npath='+json.dumps(str(R))+'\n'
(app/'rnx.toml').write_text(base)
source='''pub async fn main(args) {
    let url = args[0];
    let sql = "SELECT $1::bigint AS n, $2::text AS text";
    let value = "quote ' \\\\ 🦀";
    let first = postgres::query(url, sql, [42, value], #{}).await?;
    assert!(first.rows[0].n == 42);
    assert!(first.rows[0].text == value);
    let again = postgres::query(url, sql, [43, value], #{}).await?;
    assert!(again.rows[0].n == 43);
    assert!(polars::lit(1).is_ok());
    println!("combined: typed PostgreSQL query and Polars registered");
}
'''
(app/'main.rn').write_text(source)
logged('add-combined',command('add',app,['postgres','polars']))
m=tomllib.loads((app/'rnx.toml').read_text())
assert m['native']['postgres']['hook']=='lifecycle' and m['native']['polars']['hook']=='plain'
assert list(m['native'])==['polars','postgres']
logged('combined-lock',command('lock',app,['--offline']))
logged('combined-build',command('build',app,['--offline']))
a=artifact(app)
main=(a.parent.parent/'assembly/src/main.rs').read_text()
assert 'lifecycle' in main and 'polars' in main and 'postgres' in main
with Cluster() as c:
    logged('combined-query',command('run',app,['--',c.url]))
    c.wait_idle()
    pid=c.postmaster
    observation={'activity_after_query':c.activity(),'postmaster':pid,'typed_parameter_roundtrip':True,'both_extensions_executed':True,'wrapper':main,'artifact_sha256':sha(a)}
assert not Path('/proc',str(pid)).exists()
observation['private_postmaster_reaped']=True
save('postgres.json',observation)
dest=O/'combined';dest.mkdir()
for f in ['main.rn','rnx.toml','rnx.lock','rnx.Cargo.lock']:shutil.copyfile(app/f,dest/f)
shutil.copyfile(app/'.rnx/receipt.json',dest/'receipt.json')
print('PASS both adapters executed together; typed query and private-cluster cleanup',flush=True)
