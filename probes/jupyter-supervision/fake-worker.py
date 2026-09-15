#!/usr/bin/env python3
"""A protocol peer for incomplete boundaries; never selected by installation."""
import json,os,sys,time
r=int(sys.argv[sys.argv.index('--control-read')+1]);w=int(sys.argv[sys.argv.index('--control-write')+1])
read=os.fdopen(r,'rb',buffering=0);write=os.fdopen(w,'wb',buffering=0)
def send(value):write.write(json.dumps(value).encode()+b'\n')
send(dict(type='ready',protocol=1,rnx='0.0.0',rune='0.14.2'))
request=json.loads(read.readline());id=request['id'];nonce=request['nonce']
mode=os.environ.get('RNX_FAKE_MODE','settled')
send(dict(type='armed',id=id,epoch=1,input=1))
os.write(1,b'held\0')
for fd,name in [(1,'stdout'),(2,'stderr')]:
    marker=f'\x1eRNX-WORKER-1:{id}:{name}:{nonce}\x1f'.encode()
    if mode=='partial' and fd==2:
        os.write(fd,marker[:20]);os._exit(17)
    os.write(fd,marker)
reply=dict(type='settled',id=id,epoch=1,input=1,text_plain='42',failure=None,state_lost=False)
if mode=='malformed':del reply['failure']
send(reply)
if mode=='repeat':
    for _ in range(4):
        time.sleep(2);send(reply)
ack=read.readline()
if ack:
    with open(os.environ['RNX_FAKE_TRACE'],'wb') as f:f.write(ack)
