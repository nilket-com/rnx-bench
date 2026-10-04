"""Actual command controls: one outer Result, hooks, redaction and unchanged route table shape."""
import contextlib, http.client, json, pathlib, subprocess, sys, tempfile, time
BINARY=str(pathlib.Path(sys.argv[1]).resolve())
@contextlib.contextmanager
def host(source):
	with tempfile.TemporaryDirectory() as d:
		path=pathlib.Path(d)/'handler.rn'; path.write_text(source)
		log=pathlib.Path(d)/'log'
		with log.open('wb') as writer:
			p=subprocess.Popen([BINARY,'serve','--bind','127.0.0.1:0','--log','off',str(path)],stdout=subprocess.DEVNULL,stderr=writer)
			try:
				until=time.monotonic()+5
				while True:
					events=[json.loads(l) for l in log.read_text().splitlines()]
					ready=next((e for e in events if e['event']=='ready'),None)
					if ready: break
					assert p.poll() is None and time.monotonic()<until, events
					time.sleep(.005)
				yield int(ready['detail'].rsplit(':',1)[1]),log
			finally:
				if p.poll() is None: p.terminate()
				assert p.wait(timeout=5)==0

def get(port,path,method='GET'):
	c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
	try:
		c.request(method,path); r=c.getresponse()
		return r.status,{k.lower():v for k,v in r.getheaders() if k.lower() not in ('date','server')},r.read()
	finally:c.close()

source='''pub fn routes() {[("GET","/bare","bare"),("GET","/ok","ok"),("GET","/err","err"),("GET","/bad-ok","bad_ok"),("GET","/nested","nested"),("GET","/hello/{x}","ok")]}
pub fn bare(_) {#{status:201,headers:#{"content-type":["text/plain; charset=utf-8"]},body:"hello"}}
pub fn ok(_) {web::text(201,"hello")}
pub fn err(_) {Err("SENSITIVE-REQUEST-CONTENT\\u{1b}")}
pub fn bad_ok(_) {Ok(42)}
pub fn nested(_) {Ok(web::text(200,"hello"))}
pub fn not_found(_) {web::html(404,"missing")}
pub fn method_not_allowed(r) {web::response(405,"method","text/plain",#{"allow":r.allow})}
pub fn bad_request(_) {web::text(400,"bad")}
'''
with host(source) as (port,log):
	assert get(port,'/bare')==get(port,'/ok')
	assert get(port,'/ok','HEAD')[2]==b''
	for path in ['/err','/bad-ok','/nested']: assert get(port,path)[0::2]==(500,b'')
	assert get(port,'/missing')[0::2]==(404,b'missing')
	r=get(port,'/ok','POST'); assert r[0]==405 and r[1]['allow']=='GET, HEAD'
	assert get(port,'/hello/%FF')[0::2]==(400,b'bad')
	time.sleep(.05)
	text=log.read_text(); assert 'SENSITIVE-REQUEST-CONTENT' not in text
	assert 'handler returned Err (value redacted)' in text
print('bare/Ok parity, HEAD, Err redaction, invalid/nested Ok and all hooks PASS')
for name,status,path,method in [('not_found',404,'/absent','GET'),('method_not_allowed',405,'/','POST'),('bad_request',400,'/hello/%FF','GET')]:
	s='pub fn routes() {[("GET","/","index"),("GET","/hello/{x}","index")]} pub fn index(_) {web::text(200,"ok")} '+f'pub fn {name}(_) {{Err("private-hook-value")}}'
	with host(s) as (port,log):
		assert get(port,path,method)[0::2]==(500,b'')
		time.sleep(.01); assert 'private-hook-value' not in log.read_text()
print('Err from every reserved hook takes the redacted 500 path PASS')
with tempfile.TemporaryDirectory() as d:
	path=pathlib.Path(d)/'routes.rn';path.write_text('pub fn routes() {Ok([("GET","/","index")])} pub fn index(_) {web::text(200,"ok")}')
	p=subprocess.run([BINARY,'serve','--bind','127.0.0.1:0',str(path)],capture_output=True,timeout=5)
	assert p.returncode!=0 and b'ready' not in p.stderr and b'vector' in p.stderr,p.stderr
print('routes() Result remains refused PASS')

with host('pub fn main(r) { web::text(200,web::escape_html(String::from_utf8(r.body)?)) }') as (port,log):
 c=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
 c.request('POST','/',body=b'PRIVATE-OVERFLOW-CONTENT'+b'&'*((1<<20)//5+1))
 r=c.getresponse();assert r.status==500 and r.read()==b'';c.close()
 assert get(port,'/')[0]==200
 time.sleep(.02);assert 'PRIVATE-OVERFLOW-CONTENT' not in log.read_text()
print('escape expansion VM error gives empty redacted 500, then a subsequent request succeeds PASS')
