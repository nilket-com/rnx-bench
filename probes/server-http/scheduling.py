#!/usr/bin/env python3
"""Gate 4: client-observed HTTP latency plus independently correlated server events."""
import argparse, concurrent.futures, hashlib, json, os, pathlib, statistics, subprocess, time
from wire import Server, receive, status

CASES=('healthy-alone','awaiting-spare','cpu-spare','cpu-saturated','mixed','awaiting-batch')

class Client:
    def __init__(self,server,pool,tag,path):
        self.tag=tag
        # Clock begins before TCP connect. Request construction, transport and queueing count.
        self.start=time.perf_counter_ns()
        self.sock=server.connect()
        self.sock.sendall(server.request(path,data=b'ok',headers=f'X-Probe-Tag: {tag}\r\n'.encode()))
        self.future=pool.submit(self.read)
    def read(self):
        try:
            result=receive(self.sock);end=time.perf_counter_ns();code=status(result)
            if code==200:assert result[0].split(b'\r\n\r\n',1)[1]==b'ok'
            return {'tag':self.tag,'status':code,'client_ms':(end-self.start)/1e6,'start_ns':self.start,'end_ns':end}
        finally:self.sock.close()
    def result(self):return self.future.result(timeout=4)

def measure(case,sample,out,cpus):
    server=Server(out,extra_env={'RNX_HTTP_CPUS':cpus},small_send_buffer=False)
    pool=concurrent.futures.ThreadPoolExecutor(max_workers=24)
    clients=[]
    def send(tag,path):
        c=Client(server,pool,tag,path);clients.append(c);return c
    def request_id(tag):
        server.wait(lambda:any(e['event']=='request' and e.get('tag')==tag for e in server.events()))
        return next(e['id'] for e in server.events() if e['event']=='request' and e.get('tag')==tag)
    def phase(tag,name):
        id=request_id(tag)
        server.wait(lambda:any(e['event']=='phase' and e['id']==id and e['phase']==name for e in server.events()))
    try:
        if case=='awaiting-spare':
            send('slow','/await?bench');phase('slow','await-start')
        elif case=='cpu-spare':
            send('slow','/cpu');phase('slow','cpu-start')
        elif case=='cpu-saturated':
            send('cpu0','/cpu');phase('cpu0','cpu-start')
            send('cpu1','/cpu');phase('cpu1','cpu-start')
        elif case=='mixed':
            send('await0','/await?mixed');phase('await0','await-start')
            send('await1','/await?mixed');phase('await1','await-start')
            send('slow','/cpu');phase('slow','cpu-start')
        elif case=='awaiting-batch':
            for n in range(16):send(f'await{n}','/await?batch')
            server.wait(lambda:sum(e['event']=='admitted' for e in server.events())==16)
            assert any(e['event']=='admitted' and e['queue']>=8 for e in server.events())
        healthy=send('healthy','/healthy')
        replies=[c.result() for c in clients]
        events=server.events()
        def item(tag,event):
            id=next(e['id'] for e in events if e['event']=='request' and e['tag']==tag)
            return next(e for e in events if e['event']==event and e.get('id')==id)
        def ph(tag,name):
            id=item(tag,'request')['id']
            return next(e for e in events if e['event']=='phase' and e['id']==id and e['phase']==name)
        for r in replies:
            cpu=(case=='cpu-spare' and r['tag']=='slow') or (case=='cpu-saturated' and r['tag'].startswith('cpu')) or (case=='mixed' and r['tag']=='slow')
            assert r['status']==(500 if cpu else 200),(case,r)
            r['id']=item(r['tag'],'request')['id']
            r['worker']=item(r['tag'],'dispatch')['worker']
            r['queue_ms']=item(r['tag'],'dispatch')['ms']-item(r['tag'],'request')['ms']
            r['dispatch_to_vm_ms']=item(r['tag'],'vm_start')['ms']-item(r['tag'],'dispatch')['ms']
            r['build_ms']=item(r['tag'],'built')['build_ms']
        h=next(r for r in replies if r['tag']=='healthy')
        response=item('healthy','response')['ms'];arrival=item('healthy','request')['ms']
        assertions=[];extra={}
        if case=='awaiting-spare':
            assert ph('slow','await-start')['ms']<arrival<response<ph('slow','await-end')['ms']
            assert item('slow','dispatch')['worker']!=h['worker']
            assertions.append('healthy finishes during awaited slow request on spare worker')
        elif case=='cpu-spare':
            assert ph('slow','cpu-start')['ms']<arrival<response<item('slow','fault')['ms']
            assert item('slow','dispatch')['worker']!=h['worker']
            assertions.append('healthy finishes during CPU loop on spare worker')
        elif case=='cpu-saturated':
            assert item('cpu0','dispatch')['worker']!=item('cpu1','dispatch')['worker']
            for tag in ('cpu0','cpu1'):
                assert ph(tag,'cpu-start')['ms']<arrival<item(tag,'fault')['ms']
            blocking=next(tag for tag in ('cpu0','cpu1') if item(tag,'dispatch')['worker']==h['worker'])
            assert item('healthy','vm_start')['ms']>=item(blocking,'fault')['ms']
            assertions.append('both workers busy at healthy arrival; selected worker starts it only after CPU halt')
        elif case=='mixed':
            cw=item('slow','dispatch')['worker']
            blocked=next(tag for tag in ('await0','await1') if item(tag,'dispatch')['worker']==cw)
            other=next(tag for tag in ('await0','await1') if tag!=blocked)
            nominal=ph(blocked,'await-start')['ms']+40
            assert ph('slow','cpu-start')['ms']<nominal<item('slow','fault')['ms']
            assert ph(blocked,'await-end')['ms']>=item('slow','fault')['ms']
            assert h['worker']!=cw and response<item('slow','fault')['ms']
            extra={'blocked_await_ms':ph(blocked,'await-end')['ms']-ph(blocked,'await-start')['ms'],
                   'other_await_ms':ph(other,'await-end')['ms']-ph(other,'await-start')['ms']}
            assertions.append('timer becomes due inside same-worker CPU loop and cannot complete until halt')
        elif case=='awaiting-batch':
            assert item('healthy','admitted')['queue']>0
            dispatches=[e['id'] for e in events if e['event']=='dispatch']
            assert dispatches[-1]==h['id'] and len(dispatches)==17
            extra={'batch_ms':(max(r['end_ns'] for r in replies)-min(r['start_ns'] for r in replies))/1e6}
            extra['finite_batch_per_s']=17000/extra['batch_ms']
            assertions.append('healthy was centrally queued behind all sixteen requests')
        server.wait(lambda:sum(e['event']=='teardown' for e in server.events())==len(clients))
        row={'case':case,'sample':sample,'healthy_ms':h['client_ms'],'healthy_queue_ms':h['queue_ms'],
             'healthy_dispatch_to_vm_ms':h['dispatch_to_vm_ms'],'healthy_build_ms':h['build_ms'],
             'build_total_ms':sum(r['build_ms'] for r in replies),'assertions':assertions,'requests':replies,**extra}
    finally:
        try:server.close()
        finally:pool.shutdown(wait=True,cancel_futures=True)
    events=server.events();closed=next(e for e in events if e['event']=='closed');ready=next(e for e in events if e['event']=='ready')
    assert closed['builds']==len(clients)+1==closed['retired']
    assert closed['sockets']==0 and closed['connections']==0 and closed['active']==[0,0]
    assert sorted((e['role'],e['cpu']) for e in events if e['event']=='affinity')==list(enumerate(map(int,cpus.split(','))))
    row.update(peak_increase_bytes=closed['peak_bytes']-ready['live_bytes'],closed=closed)
    (out/'measurement.json').write_text(json.dumps(row,indent=2)+'\n')
    return row

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True,type=pathlib.Path);ap.add_argument('--samples',type=int,default=7)
    ap.add_argument('--cpus',default='2,4,6');ap.add_argument('--client-cpu',type=int,default=8);args=ap.parse_args()
    assert args.samples>0
    cpus=list(map(int,args.cpus.split(',')));assert len(cpus)==3 and len(set(cpus+[args.client_cpu]))==4
    assert set(cpus+[args.client_cpu])<=os.sched_getaffinity(0)
    os.sched_setaffinity(0,{args.client_cpu});args.output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for sample in range(args.samples):
        for case in CASES:
            rows.append(measure(case,sample,args.output/f'{sample}-{case}',args.cpus))
    summary={case:{'median_ms':statistics.median(r['healthy_ms'] for r in rows if r['case']==case),
                   'max_ms':max(r['healthy_ms'] for r in rows if r['case']==case)} for case in CASES}
    (args.output/'results.json').write_text(json.dumps({'summary':summary,'rows':rows},indent=2)+'\n')
    conditions={'driver_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'samples':args.samples,
                'worker_cpus':cpus[:2],'coordinator_cpu':cpus[2],'client_cpu':args.client_cpu,
                'cpu':subprocess.check_output(['lscpu'],text=True),'cases':CASES,'clock':'client perf_counter_ns before connect to complete response plus EOF'}
    (args.output/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
