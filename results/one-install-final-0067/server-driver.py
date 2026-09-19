#!/usr/bin/env python3
"""Ordinary executable: public API path works; test-only registrations do not."""
import json,os,pathlib,signal,socket,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1];PACKAGE=BENCH.parent/'rnx/servers/http-postgres'
sys.path.insert(0,str(HERE.parent/'server-shutdown'));sys.path.insert(0,str(HERE.parent/'postgres'))
from wire import Server,status
from cluster import Cluster
out=pathlib.Path('/home/me/work/rnx-bench/results/one-install-final-0067/server')
binary=pathlib.Path('/home/me/work/rnx-bench/probes/one-install-final/target/server-target/release/rnx-http-postgres')
os.environ.update(RNX_SERVER_BINARY=str(binary),RNX_SERVER_PROGRAM=str(PACKAGE/'examples/app.rn'))
with Cluster() as c:
    c.sql('CREATE TABLE audit(tag text NOT NULL)')
    env={'RNX_POOL_URL':c.url,'RNX_POOL_STALL_DRIVER':'1','RNX_HTTP_SMALL_SEND_BUFFER':'1'}
    child_input,parent_input=socket.socketpair()
    s=Server(out,extra_env=env,small_send_buffer=False,stdin=child_input)
    try:
        reply=s.raw(s.request(data=b'public API'))
        assert status(reply)==200 and reply[0].endswith(b'public API')
        assert status(s.raw(s.request('/db?normal')))==200
        assert c.sql("SELECT count(*) FROM audit WHERE tag='normal'").stdout.strip()=='1'
        assert status(s.raw(s.request('/db?fail')))==500
        assert c.sql("SELECT count(*) FROM audit WHERE tag='fail'").stdout.strip()=='0'
        start=time.monotonic();s.close();elapsed=time.monotonic()-start
        closed=next(e for e in s.events() if e['event']=='closed');assert closed['inherited_sockets']==1 and closed['sockets']==0
        s=None
        assert elapsed<2,elapsed
        assert c.sql("SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE 'rnx-pool-%'").stdout.strip()=='0'
        refused=subprocess.run([str(binary),'--program',str(PACKAGE/'examples/fixture.rn')],env=os.environ|env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
        assert refused.returncode==1 and b'Missing item' in refused.stderr,refused
        assert b'app' in refused.stderr and not refused.stdout
        (out/'fixture-refusal.txt').write_bytes(refused.stderr)
        (out/'result.json').write_text(json.dumps({'inherited_socket_preserved':True,'ordinary_echo':200,'committed':1,'failed_transaction_rows':0,'ignored_driver_injection':True,'shutdown_seconds':elapsed,'test_fixture_exit':refused.returncode,'pooled_backends_after':0},indent=2)+'\n')
    finally:
        if s is not None:s.close()
        child_input.close();parent_input.close()
print('PASS normal executable, rollback, ignored driver injection, missing test-only functions')
