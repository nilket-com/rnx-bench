#!/usr/bin/env python3
import argparse,concurrent.futures,hashlib,json,pathlib,sys,time
from wire import Server,status,reset
from proxy import Proxy
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'postgres'))
from cluster import Cluster

def scalar(c,sql):return c.sql(sql).stdout.strip()
def wait_sql(c,sql,want,seconds=3):
    end=time.monotonic()+seconds
    while (v:=scalar(c,sql))!=want:
        assert time.monotonic()<end,(sql,v,want)
        time.sleep(.01)
    return v

def case(c,out,mode):
    c.sql('TRUNCATE audit')
    proxy=Proxy(c.root/f'proxy-{mode}',c.root)
    s=None;ex=concurrent.futures.ThreadPoolExecutor(2);obs={'case':mode}
    try:
        url=f'postgresql:///postgres?host={proxy.path}'
        s=Server(out,extra_env={'RNX_POOL_URL':url},small_send_buffer=False)
        events=lambda kind:[e for e in s.events() if e['event']==kind]
        initial=[e['pid'] for e in events('pool_connect')];assert len(initial)==4
        assert all(e['drivers']==2 and e['runtime_tasks']==2 and e['idle']==2 and e['leases']==0 for e in events('pool_ready'))
        assert scalar(c,"SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE 'rnx-pool-%'")=='4'
        obs['idle_before']={'backend_pids':initial,'driver_tasks':4,'handler_leases':0}
        hold=mode in ('rollback','rollback-loss','commit-loss','commit-cancel')
        if hold:proxy.hold('COMMIT' if mode in ('commit-loss','commit-cancel') else 'ROLLBACK')
        query='ok' if mode in ('commit-loss','commit-cancel') else 'long' if mode in ('cancel','connection-loss') else 'budget' if mode=='budget' else 'fail'
        sock=None
        if mode in ('cancel','commit-cancel'):
            sock=s.connect();sock.sendall(s.request('/db?'+query))
        else:response=ex.submit(s.raw,s.request('/db?'+query))
        s.wait(lambda:len(events('lease'))==1);lease=events('lease')[0];pid=lease['pid'];rid=lease['id']
        if hold:
            assert proxy.held.wait(3),s.events()
            assert not any(e['id']==rid for e in events('tx_ack'))
            assert not any(e['id']==rid for e in events('teardown'))
            # The observer sees the actual outcome while the owner still has no acknowledgement.
            obs['visible_while_unacknowledged']=scalar(c,'SELECT count(*) FROM audit')
            assert obs['visible_while_unacknowledged']==('1' if mode in ('commit-loss','commit-cancel') else '0')
            obs['barrier']=list(proxy.events)[-1]
            s.wait(lambda:any(e['event']=='sample' and sum(e['active'])==1 and e['ms']>events('tx_finish_start')[-1]['ms'] for e in s.events()))
            assert not any(e['id']==rid for e in events('teardown'))
            if mode=='commit-cancel':
                reset(sock)
                s.wait(lambda:any(e['id']==rid for e in events('request_cancel_signal')))
                assert not any(e['id']==rid for e in events('teardown'))
            if mode=='rollback-loss':
                assert scalar(c,f'SELECT pg_terminate_backend({pid})')=='t'
            proxy.release(cut=mode!='rollback')
        if mode in ('cancel','connection-loss'):
            wait_sql(c,f"SELECT count(*) FROM pg_stat_activity WHERE pid={pid} AND state='active' AND query='SELECT pg_sleep(120)'",'1')
            if mode in ('cancel','commit-cancel'):reset(sock)
            else:assert scalar(c,f'SELECT pg_terminate_backend({pid})')=='t'
        if mode not in ('cancel','commit-cancel'):
            r=response.result(5);obs['status']=status(r);assert obs['status']==500
        s.wait(lambda:any(e['id']==rid for e in events('teardown')),4)
        error=[e for e in events('tx_finish_error') if e['id']==rid]
        if mode in ('rollback-loss','commit-loss','commit-cancel','connection-loss'):
            assert len(error)==1,error
            retired=[e for e in events('pool_retire') if e['id']==rid];assert len(retired)==1
            if mode in ('commit-loss','commit-cancel'):assert error[0]['category']=='ambiguous commit; no retry'
            obs['failure']=error[0]
        else:
            assert not error
            assert any(e['id']==rid and e['command']=='ROLLBACK' for e in events('tx_ack'))
        assert scalar(c,'SELECT count(*) FROM audit')==('1' if mode in ('commit-loss','commit-cancel') else '0')
        # Sequential requests visit both workers. The original worker must reuse
        # the acknowledged lease or use its newly connected replacement.
        for _ in range(2):assert status(s.raw(s.request('/db?next')))==200
        later=[e for e in events('lease') if e['worker']==lease['worker'] and e['id']!=rid]
        assert len(later)==1,later
        nextpid=later[0]['pid'];obs.update(original_pid=pid,next_pid=nextpid)
        if error:assert nextpid!=pid and nextpid not in initial
        else:assert nextpid==pid
        assert scalar(c,'SELECT count(*) FROM audit')==('3' if mode in ('commit-loss','commit-cancel') else '2')
        if mode in ('commit-loss','commit-cancel'):
            commits=[e for e in proxy.events if e.get('sql')=='COMMIT' and e.get('pid')==pid]
            assert len(commits)==1;obs['commit_attempts']=len(commits)
        obs['idle_after']=[e for e in events('pool_state')][-2:]
        last=events('teardown')[-1]['ms']
        s.wait(lambda:any(e['event']=='sample' and sum(e['active'])==0 and e['connections']==0 and e['ms']>last for e in s.events()))
        fds=[]
        for fd in pathlib.Path(f'/proc/{s.p.pid}/fd').iterdir():
            try:
                target=str(fd.readlink())
                if target.startswith('socket:'):fds.append([int(fd.name),target])
            except FileNotFoundError:pass
        assert len(fds)==5,fds  # four pool sockets and the listener, no HTTP clients
        obs['idle_socket_descriptors']=fds
        assert scalar(c,"SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE 'rnx-pool-%'")=='4'
        s.close();s=None
        ev=[json.loads(x) for x in (out/'events.jsonl').read_text().splitlines()]
        closed=[e for e in ev if e['event']=='pool_closed'];assert len(closed)==2
        assert all(e['drivers']==e['runtime_tasks']==e['idle']==e['leases']==0 for e in closed)
        wait_sql(c,"SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE 'rnx-pool-%'",'0')
        obs['pool_closed']=closed;obs['backend_count_after']=0
    finally:
        proxy.release(cut=True)
        try:
            if s is not None:s.close()
        finally:proxy.close();ex.shutdown(wait=True,cancel_futures=True)
    (out/'proxy.json').write_text(json.dumps(proxy.events,indent=2)+'\n')
    (out/'observations.json').write_text(json.dumps(obs,indent=2)+'\n')
    return obs

def contention(c,out):
    c.sql('TRUNCATE audit');proxy=Proxy(c.root/'proxy-contention',c.root);s=None;sockets=[]
    try:
        s=Server(out,extra_env={'RNX_POOL_URL':f'postgresql:///postgres?host={proxy.path}'},small_send_buffer=False)
        for _ in range(4):
            sock=s.connect();sock.sendall(s.request('/db?long'));sockets.append(sock)
        wait_sql(c,"SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE 'rnx-pool-%' AND query='SELECT pg_sleep(120)' AND state='active'",'4')
        for _ in range(4):
            sock=s.connect();sock.sendall(s.request('/db?long'));sockets.append(sock)
        s.wait(lambda:any(e['event']=='sample' and e['active']==[4,4] for e in s.events()))
        leases=[e for e in s.events() if e['event']=='lease'];assert len(leases)==4
        builds=[e for e in s.events() if e['event']=='built'];assert len(builds)==4
        for sock in sockets:reset(sock)
        sockets=[]
        s.wait(lambda:len([e for e in s.events() if e['event']=='checkout_error'])==4)
        s.wait(lambda:len([e for e in s.events() if e['event']=='teardown'])==4)
        assert scalar(c,'SELECT count(*) FROM audit')=='0'
        assert status(s.raw(s.request('/db?next')))==200
        s.close();s=None
        wait_sql(c,"SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE 'rnx-pool-%'",'0')
    finally:
        for sock in sockets:reset(sock)
        try:
            if s is not None:s.close()
        finally:proxy.close()
    row={'case':'contention','active_http':8,'leased_connections':4,'waiting_without_context':4,'cancelled_waiters':4,'backend_count_after':0}
    (out/'observations.json').write_text(json.dumps(row,indent=2)+'\n')
    (out/'proxy.json').write_text(json.dumps(proxy.events,indent=2)+'\n')
    return row

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True,type=pathlib.Path);args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    rows=[]
    with Cluster() as c:
        c.sql('CREATE TABLE audit(tag text NOT NULL)')
        for mode in ('rollback','rollback-loss','commit-loss','commit-cancel','cancel','connection-loss','budget'):
            rows.append(case(c,args.output/mode,mode))
        rows.append(contention(c,args.output/'contention'))
        cluster_events=c.events;postmaster=c.postmaster
    assert not pathlib.Path(f'/proc/{postmaster}').exists()
    (args.output/'results.json').write_text(json.dumps({'rows':rows,'postmaster_reaped':postmaster,'cluster_events':cluster_events,'postgres_version':__import__('subprocess').check_output(['/usr/lib/postgresql/18/bin/postgres','--version'],text=True).strip(),'cluster_sha256':hashlib.sha256((HERE.parent/'postgres/cluster.py').read_bytes()).hexdigest(),'hashes':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('transactions.py','proxy.py','pool.rs')}},indent=2)+'\n')
    print(json.dumps([{'case':r['case'],'before':r.get('original_pid'),'next':r.get('next_pid'),'backends_after':r['backend_count_after']} for r in rows],indent=2))
if __name__=='__main__':main()
