#!/usr/bin/env python3
import http.server,json,os,pathlib,signal,socket,statistics,subprocess,sys,threading,time
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parents[2];OUT=ROOT/'results/http-lifecycle-0055'
sys.path.insert(0,str(ROOT.parent/'rnx/tests'))
from worker_parent import Parent
os.sched_setaffinity(0,{4})
seen=threading.Event();counts={'connections':0,'requests':0}
class Server(http.server.ThreadingHTTPServer):
    daemon_threads=True
    def get_request(self):
        stream,addr=super().get_request();counts['connections']+=1;return stream,addr
class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def setup(self):
        super().setup();self.connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
    def log_message(self,*args):pass
    def do_GET(self):
        counts['requests']+=1
        if self.path=='/hang':
            seen.set();self.connection.settimeout(5)
            assert self.connection.recv(1)==b'';return
        self.send_response(200);self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'ok');self.wfile.flush()
server=Server(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever);thread.start()
env={k:v for k,v in os.environ.items() if k.lower() not in ['http_proxy','https_proxy','all_proxy','no_proxy'] and not k.startswith('RNX_')};env.update(TERM='xterm',RNX_CONFIG='/nonexistent-rnx-0055-config')
bins={'before':os.environ.get('RNX_HTTP_BEFORE','/tmp/rnx-0055-baseline/rnx'),'after':str(ROOT.parent/'rnx/target/release/rnx')}
results={};url='http://127.0.0.1:%s'%server.server_port
try:
    for label in ['before','after','after','before']:
        record=results.setdefault(label,[]);w=Parent(bins[label],env);base=counts.copy()
        try:
            assert w.execute('http::get('+json.dumps(url+'/ok')+').await?.status')[0]['text_plain']=='200'
            times=[]
            for _ in range(20):
                start=time.perf_counter();reply=w.execute('http::get('+json.dumps(url+'/ok')+').await?.status')[0];times.append((time.perf_counter()-start)*1000);assert reply['text_plain']=='200',reply
            pooled=counts['connections']-base['connections'];assert pooled==1,pooled
            seen.clear();w.begin('http::get('+json.dumps(url+'/hang')+').await?');assert w.message()['type']=='armed';assert seen.wait(2)
            start=time.perf_counter();w.p.send_signal(signal.SIGINT);reply,_=w.settled();cancel=(time.perf_counter()-start)*1000
            assert reply['failure']['category']=='interrupted',reply;w.handoff()
            record.append({'sequential_ms':times,'median_ms':statistics.median(times),'connections_for_21_requests':pooled,'signal_to_settled_ms':cancel})
        finally:w.close()
    # Default binaries expose allocator accounting through session inspection.
    for label,binary in bins.items():
        p=subprocess.run([binary,'--no-splash'],input=':memory\nlet q = http::get('+json.dumps(url+'/ok')+');\n:memory\n:reset\n:memory\n:q\n',env=env,text=True,capture_output=True,timeout=5)
        assert p.returncode==0,p.stderr
        results[label+'-allocation-transcript']={'stdout':p.stdout,'stderr':p.stderr}
    for label,binary in bins.items():
        source='let q = http::get('+json.dumps(url+'/hang')+'); select { _ = q => (), _ = time::sleep(30) => () };\n:memory\n:reset\n:memory\ntime::sleep(50).await?\n:memory\n:q\n'
        p=subprocess.run([binary,'--no-splash'],input=source,env=env,text=True,capture_output=True,timeout=5)
        assert p.returncode==0 and not p.stderr,(p.returncode,p.stderr)
        results[label+'-transport-allocation-transcript']={'stdout':p.stdout,'stderr':p.stderr,'stages':['held before reset','after logical reset','after runtime progress']}
finally:server.shutdown();server.server_close();thread.join()
(OUT/'http-cost.json').write_text(json.dumps(results,indent=2)+'\n')
print('allocation transcripts recorded; fixture TCP_NODELAY enabled')
for k in bins:print(k,[(r['median_ms'],r['signal_to_settled_ms']) for r in results[k]])
