#!/usr/bin/env python3
"""Integrate the accepted SQLSTATE rule through HTTP -> COMMIT -> retirement."""
import json,os,pathlib,sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1];ROOT=BENCH.parent/'rnx';PKG=ROOT/'servers/http-postgres'
sys.path.insert(0,str(HERE.parent/'server-transactions'));sys.path.insert(0,str(HERE.parent/'postgres'))
from wire import Server,status
from proxy import Proxy
from cluster import Cluster
os.environ.update(RNX_SERVER_BINARY=str(PKG/'target/release/rnx-http-postgres'),RNX_SERVER_PROGRAM=str(PKG/'examples/fixture.rn'))
OUT=BENCH/'results/server-extraction-0056/classification';OUT.mkdir(parents=True,exist_ok=True)
rows=[]
with Cluster() as c:
    c.sql("CREATE TABLE audit(tag text NOT NULL); CREATE FUNCTION reject_commit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$; CREATE CONSTRAINT TRIGGER reject_at_commit AFTER INSERT ON audit DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION reject_commit();")
    for code in ['23503','40001','40P01','40003']:
        # Deliberate SQLSTATE injection verifies routing in the extracted owner;
        # real constraint/serialization/deadlock mechanisms are gate 3's evidence.
        c.sql(f"TRUNCATE audit; CREATE OR REPLACE FUNCTION reject_commit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.tag='ok' THEN RAISE EXCEPTION USING ERRCODE='{code}', MESSAGE='owner classification fixture'; END IF; RETURN NEW; END $$")
        proxy=Proxy(c.root/('proxy-'+code),c.root);s=None
        try:
            s=Server(OUT/code,extra_env={'RNX_POOL_URL':f'postgresql:///postgres?host={proxy.path}'},small_send_buffer=False)
            assert status(s.raw(s.request('/db?ok')))==500
            errors=[e for e in s.events() if e['event']=='tx_finish_error'];assert len(errors)==1
            error=errors[0];assert error['sqlstate']==code,error
            assert error['category']==('ambiguous commit; no retry' if code=='40003' else 'commit rejected; retired; no retry')
            assert c.sql('SELECT count(*) FROM audit').stdout.strip()=='0'
            assert len([e for e in proxy.events if e.get('pid')==error['pid'] and e.get('sql')=='COMMIT'])==1
            lease=next(e for e in s.events() if e['event']=='lease' and e['pid']==error['pid'])
            for _ in range(2):assert status(s.raw(s.request('/db?next')))==200
            later=[e for e in s.events() if e['event']=='lease' and e['worker']==lease['worker'] and e['id']!=lease['id']];assert len(later)==1 and later[0]['pid']!=lease['pid']
            rows.append({'sqlstate':code,'category':error['category'],'old_pid':lease['pid'],'new_pid':later[0]['pid'],'commit_attempts':1,'victim_rows_after':0})
            s.close();s=None
            assert c.sql("SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE 'rnx-pool-%'").stdout.strip()=='0'
            (OUT/code/'proxy.json').write_text(json.dumps(proxy.events,indent=2)+'\n')
        finally:
            if s is not None:s.close()
            proxy.close()
(OUT/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
