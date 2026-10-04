"""Actual command controls, with startup table side effects counted independently."""
import contextlib,http.client,json,pathlib,socket,subprocess,sys,tempfile,time
BINARY=str(pathlib.Path(sys.argv[1]).resolve())
def call(port,path,method='GET'):
 c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
 try:
  c.request(method,path);r=c.getresponse();return r.status,dict(r.getheaders()),r.read()
 finally:c.close()
@contextlib.contextmanager
def host(source, timeout=100):
 with tempfile.TemporaryDirectory() as d:
  path=pathlib.Path(d)/'handler.rn';path.write_text(source);log=pathlib.Path(d)/'log';writer=log.open('wb')
  p=subprocess.Popen([BINARY,'serve','--bind','127.0.0.1:0','--request-timeout-ms',str(timeout),'--log','off',str(path)],stdout=subprocess.DEVNULL,stderr=writer)
  try:
   deadline=time.monotonic()+5
   while True:
    data=log.read_text();events=[json.loads(l) for l in data.splitlines()];ready=next((e for e in events if e['event']=='ready'),None)
    if ready:break
    assert p.poll() is None, data
    assert time.monotonic()<deadline,data;time.sleep(.005)
   yield int(ready['detail'].rsplit(':',1)[1]),log
  finally:
   if p.poll() is None:p.terminate()
   assert p.wait(timeout=5)==0;writer.close()
def refuses(source,want):
 with tempfile.TemporaryDirectory() as d:
  path=pathlib.Path(d)/'invalid.rn';path.write_text(source)
  p=subprocess.run([BINARY,'serve','--bind','127.0.0.1:0','--request-timeout-ms','10','--log','off',str(path)],capture_output=True,timeout=5)
  assert p.returncode!=0
  records=[json.loads(l) for l in p.stderr.splitlines()];assert not any(r['event']=='ready' for r in records)
  assert want in p.stderr.decode(),p.stderr
  assert 'invalid.rn:' in p.stderr.decode(),p.stderr
  print('startup refused:',want)
BASE='''fn response(s,b) {#{status:s,headers:#{},body:b}}
pub fn root(_) {response(200,"root")}
pub fn hello(r) {response(200,r.params.name)}
pub fn post(r) {response(200,r.params.id)}
pub fn first(r) {response(200,r.params.x)}
pub fn other(_) {response(200,"other")}
pub fn get(_) {response(200,"get")}
pub fn head(_) {response(200,"longer-head")}
pub async fn wait(_) {time::sleep(500).await?;response(200,"wait")}
pub fn method_not_allowed(r) {#{status:405,headers:#{"allow":["FORGED"]},body:r.allow}}
pub fn not_found(r) {response(404,r.path)}
pub fn bad_request(_) {response(400,"bad")}
pub fn main(_) {panic!("unused main")}
'''
ROWS='''[("GET","/","root"),("GET","/hello/{name}","hello"),("POST","/hello/{name}","hello"),
("POST","/posts/new","other"),("GET","/posts/{id}","post"),("GET","/a/{x}","first"),("GET","/{y}/b","other"),
("GET","/a/literal/extra","other"),("GET","/head","get"),("HEAD","/head","head"),("HEAD","/head-only","head"),
("GET","/wait","wait"),("GET","/slash/","root"),("GET","/double//","root"),("GET","/Foo","root"),
("GET","/raw/{name}","raw") ]'''
with tempfile.TemporaryDirectory() as d:
 marker=pathlib.Path(d)/'count';marker.write_text('')
 source=BASE+'pub fn raw(r) {response(200,json::stringify(#{name:r.params.name,path:r.path,query:r.query})?)}\n'+f'pub fn routes() {{fs::write({json.dumps(str(marker))},fs::read({json.dumps(str(marker))})?+"x")?;{ROWS}}}'
 with host(source) as (port,log):
  for method,path,status,body in [('GET','/',200,b'root'),('GET','/hello/J%C3%BCrgen',200,'Jürgen'.encode()),('GET','/hello/a+b%20c',200,b'a+b c'),('GET','/hello/%2F',200,b'/'),('GET','/hello/%252F',200,b'%2F'),('GET','/hello/%00',200,b'\0'),('GET','/hello/%FF',400,b'bad'),('GET','/hello/%Q0',400,b'bad'),('DELETE','/hello/%FF',400,b'bad'),('GET','/hello/',404,b'/hello/'),('GET','/hello/a/b/c',404,b'/hello/a/b/c'),('GET','/hello/a/',404,b'/hello/a/'),('GET','/posts/new',405,b'POST'),('POST','/posts/new',200,b'other'),('GET','/a/b',200,b'b'),('GET','/a/literal',200,b'literal'),('GET','/a/literal/extra',200,b'other'),('HEAD','/head',200,b''),('GET','/head-only',405,b'HEAD'),('GET','/slash/',200,b'root'),('GET','/slash',404,b'/slash'),('GET','/double//',200,b'root'),('GET','/Foo',200,b'root'),('GET','/foo',404,b'/foo')]:
   result=call(port,path,method);assert (result[0],result[2])==(status,body),(method,path,result)
  r=call(port,'/hello/a','DELETE');assert r[1]['allow']=='GET, HEAD, POST' and r[2]==b'GET, HEAD, POST'
  assert call(port,'/head','HEAD')[1]['content-length']=='11'
  assert call(port,'/hello/world','HEAD')[1]['content-length']=='5'
  raw=json.loads(call(port,'/raw/a%2Fb?x=%2B')[2]);assert raw=={'name':'a/b','path':'/raw/a%2Fb','query':'x=%2B'}
  assert call(port,'/wait')[0]==504;assert call(port,'/')[0]==200
  assert marker.read_text()=='x',marker.read_text()
  assert any(json.loads(l).get('detail')=='main is unused' for l in log.read_text().splitlines())
 print('routing, hooks, HEAD, decoded/raw fields, deadline reuse and table exactly once PASS')
with host('pub fn main(r) {match r.get("params") {Some(_)=>panic!("new field"),None=>{}} match r.get("allow") {Some(_)=>panic!("new field"),None=>{}} #{status:201,headers:#{},body:"legacy"}}') as (port,_):
 assert call(port,'/anything','DELETE')[0:3:2]==(201,b'legacy')
print('legacy main-only exact shape and dispatch PASS')
for rows,want in [('[("GET","/","missing")]','one-argument'),('[("GET","/{x}","root"),("POST","/{y}","root")]','renamings'),('[("GET","/","root"),("GET","/","root")]','duplicate'),('[("GET","/*","root")]','wildcard'),('[("GET","/","not_found")]','reserved')]:refuses(BASE+f'pub fn routes() {{{rows}}}',want)
refuses('pub fn routes() {loop {}}','budget')
refuses('pub async fn routes() {time::sleep(500).await?;[]}','timed out')
refuses('pub fn routes() {panic!("startup-fault")}','startup-fault')
with host('pub fn routes() {[("GET","/","ok")]} pub fn ok(_) {#{status:200,headers:#{},body:"ok"}} pub fn not_found(_) {#{status:200,headers:#{},body:"wrong"}}') as (port,_):assert call(port,'/absent')[0]==500
with host('pub fn routes() {[("HEAD","/","ok")]} pub fn ok(_) {#{status:200,headers:#{},body:"ok"}}') as (port,_):assert call(port,'/','GET')[0]==405 and call(port,'/','GET')[1]['allow']=='HEAD';assert call(port,'/absent')[0]==404
print('absent hooks and wrong-status hook PASS')
print('ALL ROUTE HOST CONTROLS PASS')
