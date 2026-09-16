#!/usr/bin/env python3
import json, os, pathlib, signal, sys, time, fcntl
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent
BENCH=HERE.parents[1];ROOT=BENCH.parent/'rnx';PACKAGE=ROOT/'servers/http-postgres'
sys.path.insert(0,str(HERE.parent/'server-shutdown'))
sys.path.insert(0,str(HERE.parent/'postgres'))
from wire import Server
from cluster import Cluster
out=BENCH/'results/server-extraction-0056/blocked-stderr'
os.environ.update(RNX_SERVER_BINARY=str(PACKAGE/'target/release/rnx-http-postgres'),RNX_SERVER_PROGRAM=str(PACKAGE/'examples/fixture.rn'))
read,write=os.pipe();os.set_blocking(write,False);filled=0
try:
    while True:filled+=os.write(write,b'x'*4096)
except BlockingIOError:pass
capacity=fcntl.fcntl(write,fcntl.F_GETPIPE_SZ)
assert filled==capacity
os.set_blocking(write,True)
s=None;sock=None
try:
    with Cluster() as c:
        c.sql('CREATE TABLE audit(tag text NOT NULL)')
        s=Server(out,extra_env={'RNX_POOL_URL':c.url},small_send_buffer=False,stderr=write)
        sock=s.connect();sock.sendall(s.request('/healthy?shutdown-stall'))
        s.wait(lambda:any(e['event']=='native_stall_start' for e in s.events()))
        start=time.monotonic();code=s.close(signal.SIGTERM,expect_success=False);elapsed=time.monotonic()-start
        assert code==1 and 4.8<=elapsed<6.5,(code,elapsed)
        failed=[e for e in s.events() if e['event']=='shutdown_failed'];assert len(failed)==1
        assert failed[0]['reason']=='overall deadline'
        assert failed[0]['requests']==[1] and sum(failed[0]['active'])==1 and len(failed[0]['workers_unjoined'])==1
        assert not any(e['event'] in ('closed','native_stall_end') for e in s.events())
        os.close(write);write=None
        payload=os.read(read,capacity+4096);assert payload==b'x'*filled
        end=time.monotonic()+5
        while c.sql("SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE 'rnx-pool-%'").stdout.strip()!='0':
            assert time.monotonic()<end;time.sleep(.01)
        (out/'result.json').write_text(json.dumps({'exit':code,'signal_to_exit_ms':elapsed*1000,'stderr_capacity':capacity,'unread_bytes_through_exit':filled,'failure':failed[0],'backends_after':0},indent=2)+'\n')
        s=None
finally:
    if s is not None:
        if s.p.poll() is None:os.killpg(s.p.pid,signal.SIGKILL);s.p.wait()
        s.stop.set();s.monitor.join();s.log.close()
    if sock is not None:sock.close()
    if write is not None:os.close(write)
    os.close(read)
print('PASS full stderr stays unread until exit 1; owner report persisted; no clean close')
