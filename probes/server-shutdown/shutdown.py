#!/usr/bin/env python3
"""Gate 6: signal only after the required state is observed, then audit owners."""
import argparse,hashlib,json,pathlib,signal,socket,sys,threading,time,subprocess,os
from wire import Server,receive
from proxy import Proxy
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'postgres'))
from cluster import Cluster

CASES=('idle','partial-reads','awaiting','cpu','active-sql','queued-awaiting','queued-sql',
       'pending-rollback','pending-commit','rollback-deadline','commit-deadline',
       'driver-deadline','overall-deadline')
def scalar(c,sql):return c.sql(sql).stdout.strip()
def wait(fn,seconds=3):
    end=time.monotonic()+seconds
    while not fn():
        assert time.monotonic()<end,'observation deadline'
        time.sleep(.005)
class Observer:
    def __init__(self,c):
        self.c=c;self.rows=[];self.errors=[];self.stop=threading.Event()
        self.thread=threading.Thread(target=self.run);self.thread.start()
    def run(self):
        try:
            while not self.stop.is_set():
                rows=scalar(self.c,"SELECT coalesce(json_agg(json_build_object('pid',pid,'state',state,'query',query)), '[]') FROM pg_stat_activity WHERE application_name LIKE 'rnx-pool-%'")
                self.rows.append({'at':time.monotonic(),'backends':json.loads(rows)})
                self.stop.wait(.015)
        except BaseException as e:self.errors.append(repr(e))
    def close(self):self.stop.set();self.thread.join(22);assert not self.thread.is_alive();assert not self.errors,self.errors

def run_case(c,out,mode,sig):
    c.sql('TRUNCATE audit');proxy=Proxy(c.root/f'shutdown-{mode}',c.root)
    s=None;observer=None;peers=[];row={'case':mode,'signal':sig.name}
    failure=mode in ('driver-deadline','overall-deadline')
    held=mode in ('pending-rollback','pending-commit','rollback-deadline','commit-deadline')
    def open_request(path):
        sock=s.connect();sock.sendall(s.request(path));peers.append(sock)
    try:
        env={'RNX_POOL_URL':f'postgresql:///postgres?host={proxy.path}'}
        if mode=='driver-deadline':env['RNX_POOL_STALL_DRIVER']='1'
        s=Server(out,extra_env=env,small_send_buffer=False)
        ev=lambda name:[e for e in s.events() if e['event']==name]
        observer=Observer(c)
        wait(lambda:observer.rows and len(observer.rows[-1]['backends'])==4)
        if held:
            proxy.hold('COMMIT' if 'commit' in mode else 'ROLLBACK')
            open_request('/db?ok' if 'commit' in mode else '/db?fail')
            assert proxy.held.wait(3)
            row['visible_at_barrier']=scalar(c,'SELECT count(*) FROM audit')
            assert row['visible_at_barrier']==('1' if 'commit' in mode else '0')
        elif mode=='partial-reads':
            a=s.connect();a.sendall(b'POST /healthy HTTP/1.1\r\n');peers.append(a)
            b=s.connect();b.sendall(b'POST /healthy HTTP/1.1\r\nHost: fixture\r\nContent-Length: 64\r\n\r\nx');peers.append(b)
            s.wait(lambda:any(e['event']=='sample' and e['connections']==2 for e in s.events()))
        elif mode=='awaiting':
            open_request('/await');s.wait(lambda:any(e.get('phase')=='await-start' for e in ev('phase')))
        elif mode=='cpu':
            open_request('/cpu');s.wait(lambda:any(e.get('phase')=='cpu-start' for e in ev('phase')))
        elif mode=='active-sql':
            open_request('/db?long')
            wait(lambda:any(b['state']=='active' and b['query']=='SELECT pg_sleep(120)' for r in observer.rows[-1:] for b in r['backends']))
        elif mode in ('queued-awaiting','queued-sql'):
            for _ in range(24):open_request('/db?long' if mode=='queued-sql' else '/await')
            s.wait(lambda:any(e['event']=='sample' and e['active']==[4,4] and e['queue']==16 for e in s.events()))
            if mode=='queued-sql':
                wait(lambda:sum(b['state']=='active' and b['query']=='SELECT pg_sleep(120)' for b in observer.rows[-1]['backends'])==4)
                assert len(ev('built'))==4
            else:s.wait(lambda:len([e for e in ev('phase') if e.get('phase')=='await-start'])==8)
        elif mode=='overall-deadline':
            open_request('/healthy?shutdown-stall');s.wait(lambda:len(ev('native_stall_start'))==1)
        before=s.events();row['built_before_signal']=len(ev('built'))
        signal_at=time.monotonic();s.p.send_signal(sig);row['signal_at']=signal_at
        s.wait(lambda:bool(ev('shutdown')))
        shutdown=ev('shutdown')[0];row['shutdown_event']=shutdown
        # Listener was closed before the shutdown event; no new admission.
        refused=False
        try:
            with socket.create_connection(('127.0.0.1',s.port),timeout=.3):pass
        except ConnectionRefusedError:refused=True
        assert refused,'listener still accepts after shutdown';row['new_connection_refused']=True
        if mode=='cpu':
            start=next(e for e in before if e.get('phase')=='cpu-start')
            assert start['ms']<shutdown['ms']
        if held:
            assert not ev('tx_ack') and not ev('teardown')
            if mode.endswith('deadline'):
                s.wait(lambda:bool(ev('tx_finish_error')),2)
                error=ev('tx_finish_error')[0];assert error['detail']=='cleanup deadline',error
                assert error['ms']>shutdown['ms'];row['completion_failure']=error
                assert 1100 <= error['ms']-ev('tx_finish_start')[0]['ms'] <= 1700
            proxy.release()
        code=s.close(sig,send_signal=False,expect_success=not failure)
        exit_at=time.monotonic();row.update(exit_code=code,signal_to_exit_ms=(exit_at-signal_at)*1000)
        events=s.events();row['client_owned_socket_report']=next((e for e in events if e['event']=='closed'),None)
        if not failure:
            closed=row['client_owned_socket_report'];assert closed['sockets']==0 and closed['active']==[0,0] and closed['connections']==0
            assert closed['builds']==closed['retired']
            assert len(ev('pool_closed'))==2 and all(e['drivers']==e['runtime_tasks']==e['leases']==e['idle']==0 for e in ev('pool_closed'))
            assert len(ev('worker_end'))==2 and all(e['tasks']==0 for e in ev('worker_end'))
            assert row['signal_to_exit_ms']<5500
            if mode=='cpu':assert any(e['ms']>shutdown['ms'] for e in ev('fault'))
            if mode in ('queued-awaiting','queued-sql'):
                queued=ev('queued_shutdown')[0]['ids'];assert len(queued)==16
                assert not set(queued)&{e['id'] for e in ev('built')}
            if mode in ('active-sql','queued-sql'):
                acks=[e for e in ev('tx_ack') if e['command']=='ROLLBACK'];assert len(acks)==(4 if mode=='queued-sql' else 1)
                assert all(e['ms']>shutdown['ms'] for e in acks)
            if held:
                if mode.endswith('deadline'):
                    assert len(ev('tx_finish_error'))==1 and not ev('tx_ack')
                    assert any(e['id']==1 for e in ev('pool_retire'))
                else:assert len(ev('tx_ack'))==1 and ev('tx_ack')[0]['ms']>shutdown['ms']
        else:
            failed=ev('shutdown_failed');assert len(failed)==1,events
            row['failed_shutdown']=failed[0]
            assert not ev('closed')
            if mode=='driver-deadline':
                assert failed[0]['reason']=='worker failure'
                forced=ev('driver_retirement_failed');assert forced and all(e['abort_joined'] for e in forced)
                assert all(e['ms']>shutdown['ms'] for e in forced)
                row['forced_driver_abort']=forced
            else:
                assert failed[0]['reason']=='overall deadline'
                assert failed[0]['requests']==[1] and len(failed[0]['workers_unjoined'])==1
                assert sum(failed[0]['active'])==1 and failed[0]['owned_sockets']
                assert 4800<=failed[0]['ms']-shutdown['ms']<=5500
                assert not ev('native_stall_end')
                assert row['signal_to_exit_ms']<6500
        # The process and its sockets are gone; independently wait for PostgreSQL.
        wait(lambda:observer.rows and observer.rows[-1]['at']>=signal_at and not observer.rows[-1]['backends'],5)
        zero=next(r['at'] for r in observer.rows if r['at']>=signal_at and not r['backends'])
        row['signal_to_backend_zero_ms']=(zero-signal_at)*1000
        row['rows_after']=scalar(c,'SELECT count(*) FROM audit')
        assert row['rows_after']==('1' if mode in ('pending-commit','commit-deadline') else '0')
        observer.close();row['observer']=observer.rows;observer=None
        row['http_connections']=[{'bytes':len(data),'end':end} for data,end in (receive(p) for p in peers)]
        assert not pathlib.Path(f'/proc/{s.p.pid}').exists()
        s=None
    finally:
        proxy.release(cut=True)
        try:
            if s is not None:
                if s.p.poll() is None:os.killpg(s.p.pid,signal.SIGKILL);s.p.wait()
                s.stop.set();s.monitor.join();s.log.close()
        finally:
            if observer is not None:observer.close()
            for peer in peers:peer.close()
            proxy.close()
    (out/'proxy.json').write_text(json.dumps(proxy.events,indent=2)+'\n')
    (out/'observations.json').write_text(json.dumps(row,indent=2)+'\n')
    return row

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True,type=pathlib.Path);ap.add_argument('--case',choices=CASES);ap.add_argument('--signal',choices=['INT','TERM'],default='TERM');a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    rows=[]
    with Cluster() as c:
        c.sql('CREATE TABLE audit(tag text NOT NULL)')
        for mode in ([a.case] if a.case else CASES):
            r=run_case(c,a.output/mode,mode,getattr(signal,'SIG'+a.signal));rows.append(r)
            print(json.dumps({k:r[k] for k in ('case','exit_code','signal_to_exit_ms','signal_to_backend_zero_ms')}),flush=True)
        pg=c.postmaster;cluster_events=c.events
    assert not pathlib.Path(f'/proc/{pg}').exists()
    (a.output/'results.json').write_text(json.dumps({'rows':rows,'postmaster_reaped':pg,'cluster_events':cluster_events,'postgres_version':subprocess.check_output(['/usr/lib/postgresql/18/bin/postgres','--version'],text=True).strip(),'hashes':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('shutdown.py','proxy.py','pool.rs')},'cluster_sha256':hashlib.sha256((HERE.parent/'postgres/cluster.py').read_bytes()).hexdigest()},indent=2)+'\n')
if __name__=='__main__':main()
