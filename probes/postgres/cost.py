"""One connection and SELECT per process, 100 runs on the established core."""
import hashlib,json,os,pathlib,shlex,subprocess
from cluster import Cluster
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/postgres-0052-adapter';OUT.mkdir(exist_ok=True,parents=True)
BIN=ROOT.parent/'rnx/adapters/postgres/target/release/rnx-pg'
with Cluster() as c:
    source='pub async fn main(_) { postgres::query('+json.dumps(c.url)+', "SELECT 1 AS n", [], #{}).await? }'
    script=c.root/'query.rn';script.write_text(source)
    env=dict(os.environ,TERM='xterm',RNX_CONFIG=str(c.root/'absent'),RNX_HISTORY=str(c.root/'history'))
    subprocess.run(['taskset','-c','4','hyperfine','-N','--warmup','10','--runs','100','--export-json',str(OUT/'query-timing.json'),shlex.join([str(BIN),'run',str(script)])],env=env,check=True)
    c.wait_idle()
    result=dict(source=source,core=4,warmups=10,runs=100,pg_version=c.sql('SELECT version()').stdout.strip(),binary_bytes=BIN.stat().st_size,sha256=hashlib.sha256(BIN.read_bytes()).hexdigest(),postmaster=c.postmaster,directory=str(c.root))
(OUT/'query-conditions.json').write_text(json.dumps(result,indent=2)+'\n')
