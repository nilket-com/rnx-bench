#!/usr/bin/env python3
"""0056 gate 5: the ordinary shipped example, driven by a separate process."""
import hashlib,json,os,pathlib,queue,signal,subprocess,sys,threading,time
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1];ROOT=BENCH.parent/'rnx';PACKAGE=ROOT/'servers/http-postgres'
sys.path.insert(0,str(HERE.parent/'server-shutdown'));sys.path.insert(0,str(HERE.parent/'postgres'))
from wire import Server
from cluster import Cluster
OUT=BENCH/'results/server-acceptance-0056/journey';OUT.mkdir(parents=True,exist_ok=True)
binary=PACKAGE/'target/plain/release/rnx-http-postgres';program=PACKAGE/'examples/app.rn'
os.environ.update(RNX_SERVER_BINARY=str(binary),RNX_SERVER_PROGRAM=str(program))
results=[];server=None;client=None
with Cluster() as cluster:
    cluster.sql('CREATE TABLE audit(tag text NOT NULL)')
    try:
        server=Server(OUT,extra_env={'RNX_POOL_URL':cluster.url},small_send_buffer=False)
        command=[sys.executable,str(HERE/'client.py'),str(server.port)]
        client=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1,start_new_session=True)
        client_pid=client.pid
        assert client_pid != server.p.pid
        incoming=queue.Queue()
        def read():
            for line in client.stdout:incoming.put(json.loads(line))
        reader=threading.Thread(target=read);reader.start()
        assert incoming.get(timeout=5)=={'ready':True}
        def send(tag,path,body='hello'):
            client.stdin.write(json.dumps({'tag':tag,'path':path,'body':body})+'\n');client.stdin.flush()
        def collect(count):
            values=[incoming.get(timeout=6) for _ in range(count)]
            assert all('error' not in v for v in values),values
            results.extend(values);return {v['tag']:v for v in values}
        def event(tag,kind):
            events=server.events();request=next(e for e in events if e['event']=='request' and e.get('tag')==tag)
            return next(e for e in events if e['event']==kind and e.get('id')==request['id'])
        for slow,path,want in [('await','/await',200),('cpu','/cpu',500)]:
            send(slow,path)
            def started():
                try:return event(slow,'vm_start') is not None
                except StopIteration:return False
            server.wait(started)
            send('healthy-'+slow,'/healthy','healthy beside '+slow)
            values=collect(2)
            assert values[slow]['status']==want and values['healthy-'+slow]['status']==200
            start=event(slow,'vm_start')['ms'];arrival=event('healthy-'+slow,'request')['ms'];finished=event('healthy-'+slow,'response')['ms'];end=event(slow,'response')['ms']
            assert start<arrival<finished<end,(slow,start,arrival,finished,end)
            assert event(slow,'dispatch')['worker']!=event('healthy-'+slow,'dispatch')['worker']
        send('rollback','/db?fail');assert collect(1)['rollback']['status']==500
        assert cluster.sql('SELECT count(*) FROM audit').stdout.strip()=='0'
        # Round-robin routing: two following database calls include the failed
        # request's worker, proving its lease is usable after rollback.
        send('next1','/db?next1');assert collect(1)['next1']['status']==200
        send('next2','/db?next2');assert collect(1)['next2']['status']==200
        assert cluster.sql('SELECT string_agg(tag,\',\' ORDER BY tag) FROM audit').stdout.strip()=='next1,next2'
        events=server.events();failed=event('rollback','request')['id'];lease=next(e for e in events if e['event']=='lease' and e['id']==failed)
        ack=next(e for e in events if e['event']=='tx_ack' and e['id']==failed);assert ack['command']=='ROLLBACK'
        later=next(e for e in events if e['event']=='lease' and e['id']!=failed and e['worker']==lease['worker'])
        assert later['pid']==lease['pid'] and later['ms']>ack['ms']
        client.stdin.write('{"quit":true}\n');client.stdin.flush();client.stdin.close()
        assert client.wait(timeout=5)==0;reader.join(2);assert not reader.is_alive();assert client.stderr.read()==''
        client=None
        before=time.monotonic();assert server.close(signal.SIGTERM)==0;shutdown_ms=(time.monotonic()-before)*1000
        events=server.events();closed=next(e for e in events if e['event']=='closed')
        assert closed['sockets']==0 and closed['active']==[0,0] and closed['builds']==closed['retired']==8
        assert all(e['tasks']==0 for e in events if e['event']=='worker_end')
        assert all(e['drivers']==e['runtime_tasks']==e['leases']==e['idle']==0 for e in events if e['event']=='pool_closed')
        assert cluster.sql("SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE 'rnx-pool-%'").stdout.strip()=='0'
        output={'client_command':command,'client_pid':client_pid,'server_pid':server.p.pid,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'program_sha256':hashlib.sha256(program.read_bytes()).hexdigest(),'requests':results,'context_build_ms':[e['build_ms'] for e in events if e['event']=='built'],'rollback_pid':lease['pid'],'reused_pid':later['pid'],'shutdown_ms':shutdown_ms,'closed':closed,'pooled_backends_after':0}
        server=None
    finally:
        if client is not None:
            if client.poll() is None:os.killpg(client.pid,signal.SIGKILL);client.wait()
        if server is not None:server.close()
output['postmaster_reaped']=cluster.postmaster;output['cluster_events']=cluster.events
(OUT/'results.json').write_text(json.dumps(output,indent=2)+'\n')
print('PASS separate client, healthy progress during await and CPU, rollback before reuse, clean shutdown')
