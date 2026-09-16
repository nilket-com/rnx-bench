#!/usr/bin/env python3
"""Raw HTTP observations; no HTTP client library can normalize these requests."""
import argparse, concurrent.futures, hashlib, json, os, pathlib, signal, socket, struct, subprocess, threading, time
HERE=pathlib.Path(__file__).resolve().parent
LIMIT=1024*1024
class Server:
    def __init__(self,out):
        self.out=out;out.mkdir(parents=True,exist_ok=True)
        self.events_path=out/'events.jsonl';self.events_path.write_text('')
        build=json.loads((HERE/'build.json').read_text());self.build=build
        env={k:v for k,v in os.environ.items() if k.lower() not in ('http_proxy','https_proxy','all_proxy','no_proxy') and k!='RNX_CONFIG'}
        env.update(RNX_HTTP_EVENTS=str(self.events_path.resolve()),TERM='dumb',RNX_HTTP_SMALL_SEND_BUFFER='1')
        self.log=(out/'server.log').open('w')
        self.p=subprocess.Popen([build['binary'],'server_http_probe::server','--exact','--ignored','--nocapture'],env=env,stdout=self.log,stderr=subprocess.STDOUT,start_new_session=True)
        self.samples=[];self.stop=threading.Event()
        self.monitor=threading.Thread(target=self.sample);self.monitor.start()
        try:self.wait(lambda:any(e['event']=='ready' for e in self.events()),10)
        except BaseException:
            if self.p.poll() is None:os.killpg(self.p.pid,signal.SIGKILL);self.p.wait()
            self.stop.set();self.monitor.join();self.log.close();raise
        self.port=int(next(e['address'] for e in self.events() if e['event']=='ready').rsplit(':',1)[1])
    def events(self):
        return [json.loads(line) for line in self.events_path.read_text().splitlines() if line.endswith('}')]
    def wait(self,predicate,seconds=3):
        end=time.monotonic()+seconds
        while not predicate():
            if self.p.poll() is not None:raise RuntimeError('server exited: '+(self.out/'server.log').read_text())
            if time.monotonic()>end:raise AssertionError('observation timeout')
            time.sleep(.005)
    def sample(self):
        while not self.stop.is_set():
            try:
                st=dict(line.split(':',1) for line in pathlib.Path(f'/proc/{self.p.pid}/status').read_text().splitlines() if ':' in line)
                fds=list(pathlib.Path(f'/proc/{self.p.pid}/fd').iterdir())
                self.samples.append({'at':time.monotonic(),'rss_kib':int(st['VmRSS'].split()[0]),'fds':len(fds)})
            except (OSError,KeyError):pass
            self.stop.wait(.01)
    def connect(self,small=False):
        s=socket.socket();s.settimeout(8)
        if small:s.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,1024)
        s.connect(('127.0.0.1',self.port));return s
    def request(self,path='/healthy',data=b'',headers=b'',method='POST'):
        return f'{method} {path} HTTP/1.1\r\nHost: fixture\r\nContent-Length: {len(data)}\r\n'.encode()+headers+b'\r\n'+data
    def raw(self,request):
        with self.connect() as s:
            try:s.sendall(request)
            except (BrokenPipeError,ConnectionResetError):pass
            return receive(s)
    def close(self,sig=signal.SIGTERM):
        if self.p.poll() is None:self.p.send_signal(sig)
        try:code=self.p.wait(timeout=7)
        except subprocess.TimeoutExpired:os.killpg(self.p.pid,signal.SIGKILL);self.p.wait();raise
        finally:
            self.stop.set();self.monitor.join();self.log.close()
            (self.out/'memory.json').write_text(json.dumps(self.samples,indent=2)+'\n')
            (self.out/'conditions.json').write_text(json.dumps(self.build|{'wire_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'sample_interval_ms':10,'small_send_buffer_bytes':16384,'cpu_affinity':sorted(os.sched_getaffinity(self.p.pid)) if self.p.poll() is None else sorted(os.sched_getaffinity(0)),'kernel':os.uname().release,'signal':sig.name},indent=2)+'\n')
        assert code==0,(code,(self.out/'server.log').read_text())
        assert any(e['event']=='closed' for e in self.events())
def receive(s):
    data=bytearray();end='eof'
    try:
        while b:=s.recv(65536):
            data.extend(b)
            assert len(data)<2*LIMIT+65536,'response unbounded'
    except ConnectionResetError:end='reset'
    return bytes(data),end
def status(result):
    data,_=result
    return int(data.split(b' ',2)[1]) if data.startswith(b'HTTP/1.') else None
def reset(s):s.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('ii',1,0));s.close()
def run(s,rows):
    def case(name,request,want,body=None):
        before=sum(e['event']=='built' for e in s.events());at=time.monotonic();r=s.raw(request);got=status(r)
        row={'case':name,'status':got,'end':r[1],'bytes':len(r[0]),'elapsed_ms':(time.monotonic()-at)*1000}
        rows.append(row);assert got==want,row
        head,_,payload=r[0].partition(b'\r\n\r\n')
        lengths=[int(f.split(b':',1)[1]) for f in head.split(b'\r\n')[1:] if f.lower().startswith(b'content-length:')]
        if lengths:assert len(lengths)==1 and len(payload)==lengths[0],row
        else:assert got in (204,304) and not payload,row
        if body is not None:assert r[0].split(b'\r\n\r\n',1)[1]==body,row
        if want in (400,404,405,413,414,415,417,431,505):assert sum(e['event']=='built' for e in s.events())==before,row
    case('HTTP 1.0 refused',s.request().replace(b'HTTP/1.1',b'HTTP/1.0'),505)
    case('echo',s.request(data=b'hello\x00\xff'),200,b'hello\x00\xff')
    case('exact body',s.request(data=b'x'*LIMIT),200,b'x'*LIMIT)
    for query in ['bad-status','extra-field','bad-header','framing','no-content']:
        case('response '+query,s.request('/healthy?'+query,data=b'x'),500)
    case('response body cap',s.request('/healthy?too-large',data=b'x'*LIMIT),500)
    case('empty 204',s.request('/healthy?no-content'),204,b'')
    case('response fields over',s.request('/healthy?headers-over'),500)
    case('response bytes over',s.request('/healthy?header-bytes-over'),500)
    for query,field_count in [('headers-exact',64),('header-bytes-exact',4)]:
        r=s.raw(s.request('/healthy?'+query));assert status(r)==200
        fields=r[0].split(b'\r\n\r\n',1)[0].split(b'\r\n')[1:];assert len(fields)==field_count
        total=sum(len(k)+len(v.strip()) for k,v in (f.split(b':',1) for f in fields))
        assert total<=16384
        if query=='header-bytes-exact':assert total==16384,total
        rows.append({'case':query,'status':200,'wire_fields':len(fields),'wire_header_bytes':total})

    r=s.raw(s.request('/healthy?raw=%00+%2F',headers=b'X-raw: one\r\nX-raw: \xff\r\n'));assert status(r)==200
    assert b'x-raw: one\r\nx-raw: \xff\r\n' in r[0] and r[0].endswith(b'raw=%00+%2F')
    rows.append({'case':'raw query and repeated non-Unicode headers','status':200})
    case('no path normalization',s.request('/he%61lthy'),404)
    case('body plus one',s.request(data=b'x'*(LIMIT+1)),413)
    case('huge declared length',b'POST /healthy HTTP/1.1\r\nHost: x\r\nContent-Length: 9223372036854775807\r\n\r\n',413)
    case('expect',s.request(headers=b'Expect: 100-continue\r\n'),417)
    case('encoding',s.request(headers=b'Content-Encoding: gzip\r\n'),415)
    case('unknown',s.request('/unknown'),404)
    case('method',s.request(method='GET'),405)
    case('absolute target',s.request('http://example.test/healthy'),400)
    case('upgrade',s.request(headers=b'Upgrade: websocket\r\n'),400)
    case('long target',s.request('/'+'x'*8192),414)
    case('exact header count',s.request(headers=b'X-a: b\r\n'*62),200,b'')
    case('too many headers',s.request(headers=b'X-a: b\r\n'*63),431)
    case('large head',s.request(headers=b'X-a: '+b'a'*32768+b'\r\n'),431)
    case('conflicting lengths',b'POST /healthy HTTP/1.1\r\nHost:x\r\nContent-Length:1\r\nContent-Length:2\r\n\r\nx',400)
    case('pipeline ignored',s.request(data=b'x')+s.request(data=b'y'),200,b'x')
    chunkhead=b'POST /healthy HTTP/1.1\r\nHost:x\r\nTransfer-Encoding: chunked\r\n\r\n'
    case('chunked',chunkhead+b'3\r\nabc\r\n0\r\n\r\n',200,b'abc')
    case('huge declared chunk',chunkhead+b'4000000000000000\r\n'+b'x'*(LIMIT+1),413)
    case('chunks over cap',chunkhead+b'100001\r\n'+b'x'*(LIMIT+1)+b'\r\n0\r\n\r\n',413)
    case('many chunks',chunkhead+b'1\r\nx\r\n'*10000+b'0\r\n\r\n',200,b'x'*10000)
    case('oversized chunk extension',chunkhead+b'1;'+b'a'*32768+b'\r\nx\r\n0\r\n\r\n',400)
    case('chunk length overflow',chunkhead+b'10000000000000000\r\n',400)
    case('trailers',chunkhead+b'0\r\nX-last: y\r\n\r\n',400)
    case('huge trailer',chunkhead+b'0\r\nX-last: '+b'x'*65536+b'\r\n\r\n',400)
    # Partial body must never be admitted, independently of whether Hyper can still reply.
    before=sum(e['event']=='built' for e in s.events())
    with s.connect() as sock:
        sock.sendall(b'POST /healthy HTTP/1.1\r\nHost:x\r\nContent-Length:10\r\n\r\nx');sock.shutdown(socket.SHUT_WR);r=receive(sock)
    assert status(r) in (None,400);assert sum(e['event']=='built' for e in s.events())==before
    rows.append({'case':'truncated body','status':status(r),'end':r[1]})
    # Separate absolute head and body clocks; these may run independently.
    def clock(which):
        with s.connect() as sock:
            at=time.monotonic()
            if which=='body':sock.sendall(b'POST /healthy HTTP/1.1\r\nHost:x\r\nContent-Length:10\r\n\r\nx')
            if which=='head':sock.sendall(b'POST /healthy HTTP/1.1\r\nHo')
            if which=='fragmented head':
                sock.sendall(b'POST /healthy HTTP/1.1\r\nX: ')
                for _ in range(4):time.sleep(1);sock.sendall(b'a')
            r=receive(sock);elapsed=time.monotonic()-at
        assert 4.7<elapsed<6.5,(which,elapsed,r)
        if which=='body':assert status(r)==408
        rows.append({'case':which+' deadline','status':status(r),'elapsed_ms':elapsed*1000,'end':r[1]})
    with concurrent.futures.ThreadPoolExecutor(4) as ex:list(ex.map(clock,['body','head','empty head','fragmented head']))
    # Connection slots are occupied by incomplete heads. No context is constructed.
    sockets=[s.connect() for _ in range(32)]
    try:
        time.sleep(.05);at=time.monotonic()
        with s.connect() as sock:r=receive(sock)
        assert status(r) is None and time.monotonic()-at<.5
        rows.append({'case':'connection saturation','end':r[1]})
    finally:
        for sock in sockets:reset(sock)
    time.sleep(.05)
    # Eight active + sixteen queued: the 25th request must be refused, not built.
    sockets=[];start_events=len(s.events())
    for i in range(24):
        sock=s.connect();sock.sendall(s.request('/await'));sockets.append(sock)
    s.wait(lambda:any(e['event']=='admitted' and e['queue']==16 and e['active']==[4,4] for e in s.events()[start_events:]))
    s.wait(lambda:sum(e['event']=='vm_start' for e in s.events()[start_events:])==8)
    before=sum(e['event']=='built' for e in s.events())
    r=s.raw(s.request());assert status(r)==503
    assert sum(e['event']=='built' for e in s.events())==before
    rows.append({'case':'queue saturation','status':503,'builds':before})
    # Remove a queued request and an active one by RST, not by timer.
    at=time.monotonic();reset(sockets[-1]);reset(sockets[0])
    for sock in sockets[1:-1]:reset(sock)
    s.wait(lambda:sum(e['event']=='teardown' for e in s.events())==sum(e['event']=='built' for e in s.events()),1)
    assert time.monotonic()-at<1
    rows.append({'case':'disconnect cleanup','elapsed_ms':(time.monotonic()-at)*1000})
    time.sleep(.05)
    # Awaited handler times out, then a healthy request still succeeds.
    at=time.monotonic();r=s.raw(s.request('/await'));elapsed=time.monotonic()-at
    assert status(r)==504 and 1.8<elapsed<3, (status(r),elapsed)
    rows.append({'case':'admitted deadline','status':504,'elapsed_ms':elapsed*1000})
    case('recovery',s.request(data=b'ok'),200,b'ok')
    case('cpu whole budget',s.request('/cpu'),500)
    case('failure',s.request('/fail'),500)
    # CPU saturation with oversized requests: parsing/refusal stays on the coordinator.
    sockets=[];cpu_start=len(s.events())
    for _ in range(8):
        sock=s.connect();sock.sendall(s.request('/cpu'));sockets.append(sock)
    s.wait(lambda:len({e['worker'] for e in s.events()[cpu_start:] if e['event']=='vm_start'})==2)
    at=time.monotonic();r=s.raw(s.request(headers=b'Expect: 100-continue\r\n'));elapsed=time.monotonic()-at
    assert status(r)==417 and elapsed<.5
    rows.append({'case':'coordinator under CPU','status':417,'elapsed_ms':elapsed*1000})
    for sock in sockets:assert status(receive(sock))==500;sock.close()
    ev=s.events()[cpu_start:];refusal=next(e for e in ev if e['event']=='response' and e['status']==417)
    starts={e['id']:e['ms'] for e in ev if e['event']=='vm_start'}
    assert any(starts[e['id']]<=refusal['ms']<=e['ms'] for e in ev if e['event']=='handler_error')
    # Native calls are a distinct negative control: timeout is not execution termination.
    start_events=len(s.events());sock=s.connect();sock.sendall(s.request('/healthy?native-stall'))
    s.wait(lambda:any(e['event']=='vm_start' for e in s.events()[start_events:]))
    r=receive(sock);sock.close();assert status(r)==504
    ev=s.events()[start_events:];start=next(e for e in ev if e['event']=='vm_start');expired=next(e for e in ev if e['event']=='deadline')
    assert not any(e['event']=='teardown' and e['id']==start['id'] for e in ev)
    assert sum(expired['active'])>=1
    s.wait(lambda:any(e['event']=='teardown' and e['id']==start['id'] for e in s.events()[start_events:]))
    end=next(e for e in s.events()[start_events:] if e['event']=='teardown' and e['id']==start['id'])
    rows.append({'case':'native call retains active slot after 504','status':504,'deadline_ms':expired['ms']-start['ms'],'teardown_ms':end['ms']-start['ms']})
    # Queue expiry with occupied executor polls. The only native stalls are the first
    # two requests; six additional active credits and the queue cannot execute yet.
    start_events=len(s.events());held=[]
    for _ in range(2):
        sock=s.connect();sock.sendall(s.request('/healthy?native-stall'));held.append(sock)
    s.wait(lambda:sum(e['event']=='vm_start' for e in s.events()[start_events:])==2)
    for _ in range(6):
        sock=s.connect();sock.sendall(s.request('/await'));held.append(sock)
    sock=s.connect();sock.sendall(s.request());held.append(sock)
    s.wait(lambda:any(e['event']=='admitted' and e['queue']==1 for e in s.events()[start_events:]))
    queued=next(e['id'] for e in s.events()[start_events:] if e['event']=='admitted' and e['queue']==1)
    r=receive(sock);assert status(r)==504
    assert not any(e['event']=='built' and e['id']==queued for e in s.events())
    for sock in held:reset(sock)
    s.wait(lambda:sum(e['event']=='teardown' for e in s.events())==sum(e['event']=='built' for e in s.events()),2)
    time.sleep(.1)
    rows.append({'case':'queued expiry without construction','status':504,'id':queued})
    # A slow reader must not keep a response indefinitely. Small receive window is verified by timing.
    with s.connect(small=True) as sock:
        sock.sendall(s.request(data=b'z'*LIMIT));time.sleep(1.4)
        # Inspect events, not drain time: buffered TCP bytes can outlive server close.
        observed=sum(e.get('result')=='write deadline' for e in s.events());assert observed>0
        rows.append({'case':'slow reader','observed_write_deadlines':observed})
        reset(sock)
    case('post slow-reader recovery',s.request(data=b'ok'),200,b'ok')
    # Three bounded receive batches, not a claim of a process-wide allocator limit.
    resource_rows=[]
    for iteration in range(3):
        sockets=[];before=sum(e['event']=='built' for e in s.events())
        for _ in range(32):
            sock=s.connect();sock.sendall(f'POST /healthy HTTP/1.1\r\nHost:x\r\nContent-Length:{LIMIT}\r\n\r\n'.encode()+b'x'*(LIMIT-1));sockets.append(sock)
        time.sleep(.2)
        sample=next(e for e in reversed(s.events()) if e['event']=='sample')
        assert sample['connections']==32 and sample['active']==[0,0] and sample['queue']==0,sample
        assert sum(e['event']=='built' for e in s.events())==before
        peak_rss=s.samples[-1]['rss_kib']
        for sock in sockets:reset(sock)
        s.wait(lambda:any(e['event']=='sample' and e['ms']>sample['ms'] and e['connections']==0 for e in s.events()),2)
        idle=next(e for e in reversed(s.events()) if e['event']=='sample')
        assert idle['live_bytes']<1024*1024,idle
        resource_rows.append({'iteration':iteration,'held_live_bytes':sample['live_bytes'],'held_rss_kib':peak_rss,'idle_live_bytes':idle['live_bytes'],'idle_rss_kib':s.samples[-1]['rss_kib']})
        # Repeated declared lengths do not allocate from that length.
        for _ in range(40):
            assert status(s.raw(b'POST /healthy HTTP/1.1\r\nHost:x\r\nContent-Length:9223372036854775807\r\n\r\n'))==413
    rows.append({'case':'resource batches','batches':resource_rows})

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=pathlib.Path,required=True);ap.add_argument('--signal',choices=['INT','TERM'],default='INT');args=ap.parse_args();rows=[];s=Server(args.output)
    try:run(s,rows)
    finally:
        try:s.close(signal.SIGINT if args.signal=='INT' else signal.SIGTERM)
        finally:(args.output/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(f'{len(rows)} raw-wire cases passed: {args.output}')
if __name__=='__main__':main()
