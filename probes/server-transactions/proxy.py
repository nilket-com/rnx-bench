"""Fixture-only PostgreSQL v3 frame relay. Withhold one command's acknowledgement."""
import pathlib,socket,struct,threading,time

def exact(s,n):
    out=bytearray()
    while len(out)<n:
        b=s.recv(n-len(out))
        if not b:raise EOFError
        out.extend(b)
    return bytes(out)
def packet(s,startup=False):
    tag=b'' if startup else exact(s,1)
    size=exact(s,4);n=struct.unpack('!I',size)[0]
    assert 4<=n<=16*1024*1024,n
    return tag+size+exact(s,n-4)

class Proxy:
    def __init__(self,path,upstream):
        self.path=path;path.mkdir(mode=0o700)
        self.upstream=str(upstream/'.s.PGSQL.5432');self.lock=threading.Lock()
        self.arm=None;self.held=threading.Event();self.action=threading.Event();self.cut=False
        self.events=[];self.peers=[];self.threads=[];self.stopping=False;self.errors=[]
        self.listener=socket.socket(socket.AF_UNIX);self.listener.bind(str(path/'.s.PGSQL.5432'));self.listener.listen();self.listener.settimeout(.1)
        self.accept=threading.Thread(target=self.accept_loop);self.accept.start()
    def record(self,**kw):
        with self.lock:self.events.append(dict(at=time.monotonic(),**kw))
    def hold(self,command):self.arm=command;self.held.clear();self.action.clear();self.cut=False
    def release(self,cut=False):self.cut=cut;self.action.set()
    def accept_loop(self):
        while not self.stopping:
            try:front,_=self.listener.accept()
            except socket.timeout:continue
            except OSError:break
            back=socket.socket(socket.AF_UNIX);back.connect(self.upstream)
            self.peers.extend([front,back]);state={'hold':False,'command':None,'pid':None}
            for fn,args in ((self.front,(front,back,state)),(self.back,(back,front,state))):
                t=threading.Thread(target=self.guard,args=(fn,args));self.threads.append(t);t.start()
    def guard(self,fn,args):
        try:fn(*args)
        except (EOFError,ConnectionError,OSError):pass
        except BaseException as e:self.errors.append(repr(e))
        finally:
            for s in args[:2]:
                try:s.shutdown(socket.SHUT_RDWR)
                except OSError:pass
    def front(self,src,dst,state):
        dst.sendall(packet(src,True))
        while True:
            data=packet(src)
            if data[:1]==b'Q':
                sql=data[5:-1].decode();self.record(event='query',pid=state['pid'],sql=sql)
                with self.lock:
                    if sql==self.arm:
                        self.arm=None;state.update(hold=True,command=sql)
            dst.sendall(data)
    def back(self,src,dst,state):
        while True:
            data=packet(src)
            if data[:1]==b'K':state['pid']=struct.unpack('!I',data[5:9])[0]
            if state['hold']:
                state['hold']=False
                self.record(event='withheld',pid=state['pid'],command=state['command'],first_type=data[:1].decode())
                self.held.set()
                if not self.action.wait(4):raise AssertionError('barrier not released')
                if self.cut:return
            dst.sendall(data)
    def close(self):
        self.stopping=True;self.action.set();self.listener.close();self.accept.join(2)
        for s in self.peers:
            try:s.shutdown(socket.SHUT_RDWR)
            except OSError:pass
            s.close()
        for t in self.threads:t.join(2);assert not t.is_alive()
        assert not self.accept.is_alive();assert not self.errors,self.errors
