"""0052 F1: URL and SQL bindings survive repeated real database calls."""
import hashlib, json, os, pathlib, subprocess, sys
from cluster import Cluster

ROOT = pathlib.Path(__file__).resolve().parents[2]
BIN = ROOT.parent/'rnx/adapters/postgres/target/release/rnx-pg'
OUT = ROOT/'results/postgres-0052-reuse'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT.parent/'rnx/tests'))
from worker_parent import Parent

results = {'sha256': hashlib.sha256(BIN.read_bytes()).hexdigest()}
with Cluster() as c:
    env = dict(os.environ, TERM='xterm', NO_COLOR='1', RNX_CONFIG=str(c.root/'absent'), RNX_HISTORY=str(c.root/'history'))
    setup = 'let url='+json.dumps(c.url)+'; let sql="SELECT $1::int8 AS n";'
    def query(n):
        return f'postgres::query(url, sql, [{n}], #{{}}).await?.rows[0].n'
    source = setup+' let a='+query(42)+'; let b='+query(43)+'; [a, b, url == '+json.dumps(c.url)+', sql == "SELECT $1::int8 AS n"]'
    for mode in ['run', 'eval']:
        if mode == 'run':
            script=c.root/'reuse.rn'; script.write_text('pub async fn main(_) { '+source+' }')
            args=['run',str(script)]
        else:
            args=['eval',source]
        r=subprocess.run([str(BIN),*args],env=env,capture_output=True,text=True,timeout=10)
        assert r.returncode==0 and r.stdout=='[42, 43, true, true]\n' and not r.stderr,r
        results[mode]=dict(source=source,stdout=r.stdout,stderr=r.stderr,exit=r.returncode)
    w=Parent(str(BIN),env)
    try:
        reply=w.execute(setup)[0]; assert reply['failure'] is None,reply
        replies=[]
        for n in [42,43]:
            reply=w.execute(query(n))[0]
            assert reply['failure'] is None and reply['text_plain']==str(n),reply
            replies.append(reply)
        reply=w.execute('[url == '+json.dumps(c.url)+', sql == "SELECT $1::int8 AS n"]')[0]
        assert reply['failure'] is None and reply['text_plain']=='[true, true]',reply
        results['retained session']=dict(calls=replies,bindings=reply)
        reply=w.execute('let pending=postgres::query(url, sql, [44], #{}); sql.push_str(" + 1"); pending.await?.rows[0].n')[0]
        assert reply['failure'] is None and reply['text_plain']=='44',reply
        results['lazy snapshot']=reply
    finally:
        w.close()
    c.wait_idle()
    results['cleanup']=dict(directory=str(c.root),postmaster=c.postmaster)
assert not c.root.exists()
(OUT/'reuse.json').write_text(json.dumps(results,indent=2)+'\n')
print('run, eval, retained session bindings and lazy SQL snapshot passed; cluster removed')
