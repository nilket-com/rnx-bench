"""Actual stock-host controls. Every subprocess is reaped, sockets and descriptors closed."""
import concurrent.futures, contextlib, fcntl, http.client, json, os, pathlib, signal, socket, subprocess, sys, tempfile, time
BINARY = pathlib.Path(sys.argv[1]).resolve()
SOURCE = '''pub async fn main(r) {
 if r.path == "/loop" { loop {} }
 if r.path == "/fail" { panic!("fixture failure"); }
 if r.path == "/secret" { panic!("{}",r.query); }
 if r.path == "/wait" { time::sleep(200).await?; }
 if r.path == "/long" { time::sleep(10000).await?; }
 if r.path == "/bad" { return #{status:200,headers:#{},body:42}; }
 if r.path == "/reserved" { return #{status:200,headers:#{"content-length":["9"]},body:""}; }
 if r.path == "/204bad" { return #{status:204,headers:#{},body:"x"}; }
 if r.path == "/204" { return #{status:204,headers:#{},body:""}; }
 if r.path == "/304" { return #{status:304,headers:#{},body:""}; }
 if r.path == "/duplicates" { return #{status:200,headers:#{"set-cookie":["a=1","b=2"]},body:r.headers["x-a"][0]}; }
 #{status:200,headers:#{},body:if r.path=="/echo" {r.body} else {"okay"}}
}'''
@contextlib.contextmanager
def server(root, extra=(), source=SOURCE, blocked=False, bind="127.0.0.1:0"):
	path=root/'handler.rn'; path.write_text(source)
	log=root/'host.log'; writer=log.open('wb')
	rd=wr=None
	if blocked:
		rd,wr=os.pipe(); flags=fcntl.fcntl(wr,fcntl.F_GETFL); err=wr
	else: err=writer
	p=subprocess.Popen([BINARY,'serve','--bind',bind,'--workers','1',*extra,path],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=err)
	try:
		deadline=time.monotonic()+8; data=b''
		while time.monotonic()<deadline:
			if blocked:
				import select
				if select.select([rd],[],[],.1)[0]: data+=os.read(rd,65536)
			else: data=log.read_bytes()
			ready=[json.loads(l) for l in data.splitlines() if l.startswith(b'{') and json.loads(l).get('event')=='ready']
			if ready: break
			assert p.poll() is None,(p.returncode,data)
			time.sleep(.005)
		else: raise AssertionError(('no ready',data))
		port=int(ready[-1]['detail'].rsplit(':',1)[1])
		yield p,port,log
		if p.poll() is None: p.send_signal(signal.SIGTERM)
		assert p.wait(timeout=4)==0,(p.returncode,log.read_bytes())
		if blocked: assert fcntl.fcntl(wr,fcntl.F_GETFL)==flags
	finally:
		if p.poll() is None: p.kill();p.wait(timeout=5)
		writer.close()
		if blocked: os.close(rd);os.close(wr)
def call(port,path='/',body=None,headers=None,method='GET'):
	c=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
	try:
		c.request(method,path,body,headers or {});r=c.getresponse();return r.status,r.getheaders(),r.read()
	finally:c.close()
def raw(port,data):
	with socket.create_connection(('127.0.0.1',port),timeout=8) as s:
		s.sendall(data);return s.recv(65536)
def status(port,path,n):
	got=call(port,path);assert got[0]==n,(path,got)
with tempfile.TemporaryDirectory(prefix='rnx-http-controls-') as temp:
	root=pathlib.Path(temp)
	for args in [[],['--workers','0'],['--bind','localhost:0'],['--log','bad'],['--workers','1','--workers','1'],['--budget','0'],['--wat'],['a','b']]:
		r=subprocess.run([BINARY,'serve',*args,'missing.rn'],capture_output=True,timeout=5)
		assert r.returncode and b'could not read' not in r.stderr,(args,r.stderr)
	print('options refused before source opening',flush=True)
	(root/'bad.rn').write_text('pub fn main(r) {\n unknown\n}\n')
	r=subprocess.run([BINARY,'serve',root/'bad.rn'],capture_output=True,timeout=8)
	assert r.returncode and b'bad.rn:2:' in r.stderr,r.stderr
	with server(root,('--log','off')) as (p,port,log):
		for path,n in [('/',200),('/secret?log-secret-canary',500),('/fail',500),('/bad',500),('/reserved',500),('/204bad',500),('/204',204),('/304',304),('/loop',500)]:
			status(port,path,n);status(port,'/',200)
		head=call(port,'/',method='HEAD');assert head[0]==200 and dict(head[1])['content-length']=='4' and head[2]==b''
		c=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
		for _ in range(3):c.request('GET','/');r=c.getresponse();assert r.status==200 and r.read()==b'okay'
		c.close()
		assert call(port,'/echo',b'a'*(1<<20),method='POST')[2]==b'a'*(1<<20)
		assert raw(port,b'POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 1048577\r\n\r\n').startswith(b'HTTP/1.1 413')
		assert raw(port,b'GET / HTTP/1.1\r\nHost: x\r\nBad Header: x\r\n\r\n').startswith(b'HTTP/1.1 400')
		assert b'HTTP/1.1 200' in raw(port,b'GET /duplicates HTTP/1.1\r\nHost: x\r\nx-a: first\r\nx-a: second\r\n\r\n')
		assert raw(port,b'GET /'+b'x'*8200+b' HTTP/1.1\r\nHost: x\r\n\r\n').startswith(b'HTTP/1.1 400')
		with socket.create_connection(('127.0.0.1',port),timeout=8) as s:
			s.sendall(b'POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 1\r\n\r\n');assert s.recv(65536).startswith(b'HTTP/1.1 408')
		# A bind collision is visible and does not construct an application-specific host.
		r=subprocess.run([BINARY,'serve','--bind',f'127.0.0.1:{port}',root/'handler.rn'],capture_output=True,timeout=8)
		assert r.returncode and b'serve bind' in r.stderr,r.stderr
		assert not raw(port,b'GET / HTTP/1.1\r\nHost: x\r\n'+b'x-a: a\r\n'*65+b'\r\n').startswith(b'HTTP/1.1 200')
		# The oversize streamed path has no Content-Length preflight.
		with socket.create_connection(('127.0.0.1',port),timeout=8) as stream:
			try: stream.sendall(b'POST /echo HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n\r\n100001\r\n'+b'a'*((1<<20)+1)+b'\r\n0\r\n\r\n')
			except BrokenPipeError: pass # Server may reject and close while the client is still sending.
			assert stream.recv(65536).startswith(b'HTTP/1.1 413')
	assert b'log_summary' in log.read_bytes() and b'log-secret-canary' not in log.read_bytes(),log.read_bytes()
	print('wire, keep-alive, limits, invalid outputs, instruction exhaustion, reuse and diagnostic privacy passed',flush=True)
	with server(root,('--request-timeout-ms','40','--log','off')) as (p,port,log):
		status(port,'/wait',504);status(port,'/',200)
		# Disconnect an active async call; it cannot occupy its slot indefinitely.
		for _ in range(8):
			s=socket.create_connection(('127.0.0.1',port));s.sendall(b'GET /long HTTP/1.1\r\nHost: x\r\n\r\n');s.close()
		time.sleep(.08);status(port,'/',200)
		with concurrent.futures.ThreadPoolExecutor(max_workers=28) as e:
			results=list(e.map(lambda _:call(port,'/wait')[0],range(28)))
		assert 503 in results and set(results)<={503,504},results
		status(port,'/',200)
	print('deadline, disconnect, bounded admission and queue expiry passed',flush=True)
	with server(root,('--grace-ms','50','--log','off')) as (p,port,log):
		s=socket.create_connection(('127.0.0.1',port));s.sendall(b'GET /long HTTP/1.1\r\nHost: x\r\n\r\n');time.sleep(.05)
		start=time.monotonic();p.send_signal(signal.SIGTERM);assert p.wait(timeout=2)==0;assert time.monotonic()-start<1;s.close()
	print('grace cancellation and joins passed',flush=True)
	with server(root,('--grace-ms','500','--log','off')) as (p,port,log):
		with concurrent.futures.ThreadPoolExecutor(max_workers=1) as e:
			answer=e.submit(call,port,'/wait');time.sleep(.06);p.send_signal(signal.SIGTERM)
			assert answer.result(timeout=2)[0]==200
			assert p.wait(timeout=2)==0
	print('active request drains within grace',flush=True)
	with server(root,('--log','off')) as (p,port,log):
		idle=[]
		try:
			for _ in range(256):
				c=http.client.HTTPConnection('127.0.0.1',port,timeout=5);c.request('GET','/');r=c.getresponse();assert r.status==200;r.read();idle.append(c)
			with socket.create_connection(('127.0.0.1',port),timeout=5) as waiting:
				waiting.sendall(b'GET / HTTP/1.1\r\nHost: x\r\n\r\n');waiting.settimeout(.1)
				try:
					data=waiting.recv(1);raise AssertionError(('connection 257 accepted/reset while full',data))
				except socket.timeout:pass
				idle.pop().close();waiting.settimeout(2);assert waiting.recv(65536).startswith(b'HTTP/1.1 200')
		finally:
			for c in idle:c.close()
	print('connection 257 waits in backlog and is served after release',flush=True)

	with server(root,('--log','off'),bind='[::1]:0') as (p,port,log):
		c=http.client.HTTPConnection('::1',port,timeout=5);c.request('GET','/');r=c.getresponse();assert r.status==200 and r.read()==b'okay';c.close()
	print('IPv6 and ephemeral ready address passed',flush=True)

	with server(root,blocked=True) as (p,port,log):
		for _ in range(1500): status(port,'/',200)
		assert p.poll() is None
	print('undrained pipe: service progresses, bounded shutdown, parent flags unchanged',flush=True)
print('ALL HOST CONTROLS PASS')
