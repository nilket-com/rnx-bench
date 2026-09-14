#!/usr/bin/env python3
"""Transport gate, not a kernel. All waits fail after five seconds."""
import argparse, json, os, pathlib, queue, secrets, subprocess, tempfile, threading, time
CAP = 2 * 1024 * 1024
TIMEOUT = 5
TRACE = []
def record(**event):
    TRACE.append(event)
    print(json.dumps(event), flush=True)
class Scanner:
    def __init__(self, marker, identity):
        self.marker, self.identity = marker, identity
        self.pending = b''
        self.data = bytearray()
        self.discarded = 0
        self.ended = False
        self.late = bytearray()
    def retain(self, b):
        n = min(len(b), CAP-len(self.data))
        self.data.extend(b[:n]); self.discarded += len(b)-n
    def feed(self, b):
        if self.ended:
            self.late.extend(b[:max(0, CAP-len(self.late))]); return
        b = self.pending + b
        i = b.find(self.marker)
        if i >= 0:
            self.retain(b[:i]); self.pending = b''; self.ended = True
            self.feed(b[i+len(self.marker):]); return
        n = max(0, len(b)-len(self.marker)+1)
        self.retain(b[:n]); self.pending = b[n:]
    def eof(self):
        if not self.ended:
            self.retain(self.pending); self.pending=b''
        return self.ended
class Worker:
    def __init__(self, binary, isolated=True):
        cr, pw = os.pipe(); pr, cw = os.pipe()
        kwargs = dict(stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.name == 'posix':
            endpoints = [cr,cw]
            kwargs['pass_fds'] = endpoints
            mechanism = 'Popen pass_fds: only child control ends inherit; worker F_SETFD FD_CLOEXEC'
        else:
            import msvcrt
            endpoints = [msvcrt.get_osfhandle(cr), msvcrt.get_osfhandle(cw)]
            for h in endpoints: os.set_handle_inheritable(h, True)
            info = subprocess.STARTUPINFO(); info.lpAttributeList = {'handle_list': endpoints}
            kwargs.update(startupinfo=info, close_fds=True)
            mechanism = 'STARTUPINFOEX handle_list plus standard handles; worker SetHandleInformation'
        try:
            self.p = subprocess.Popen([str(binary), *map(str,endpoints), 'isolated' if isolated else 'leaky'], **kwargs)
        finally:
            os.close(cr); os.close(cw)
        self.send_pipe = os.fdopen(pw,'wb', buffering=0)
        self.control = os.fdopen(pr,'rb', buffering=0)
        self.messages = queue.Queue()
        def controls():
            # Probe replies are tiny, and read limit enforces the protocol cap.
            while True:
                line = self.control.readline(256*1024+2)
                if not line: self.messages.put(None); return
                assert len(line)<=256*1024+1
                self.messages.put(json.loads(line))
        threading.Thread(target=controls,daemon=True).start()
        assert self.messages.get(timeout=TIMEOUT)['type']=='ready'
        record(test='inheritance', mechanism=mechanism, isolated=isolated)
    def send(self, msg): self.send_pipe.write(json.dumps(msg).encode()+b'\n')
    def close(self):
        if self.p.poll() is None: self.p.kill()
        self.p.wait(timeout=TIMEOUT)
        self.send_pipe.close(); self.control.close()
        self.p.stdout.close(); self.p.stderr.close()
def scanner_tests():
    marker = b'\x1eRNX-WORKER-1:4:stdout:' + b'a'*64 + b'\x1f'
    payload = b'\0\xffabc'+marker.replace(b'a'*64,b'b'*64)+marker[:-1]+b'X'
    for split in range(len(marker)+1):
        s=Scanner(marker,('worker',4,'stdout'))
        s.feed(payload+marker[:split]); s.feed(marker[split:]+b'late')
        assert s.ended and s.data==payload and s.late==b'late'
    s=Scanner(marker,('worker',4,'stdout'))
    for c in payload+marker: s.feed(bytes([c]))
    assert s.eof() and s.data==payload
    for n in range(1,len(marker)):
        s=Scanner(marker,('worker',4,'stdout')); s.feed(marker[:n])
        assert not s.eof() and s.data==marker[:n]
    record(test='scanner', marker_splits=len(marker)+1, partial_eofs=len(marker)-1, one_byte=True, result='pass')
def isolation(binary,rnx,isolated):
    with tempfile.TemporaryDirectory() as tmp:
        ready=pathlib.Path(tmp)/'ready'
        w=Worker(binary, isolated)
        try:
            w.send(dict(op='isolation',rnx=str(rnx),ready_file=str(ready)))
            spawned=w.messages.get(timeout=TIMEOUT); assert spawned['type']=='spawned'
            until=time.monotonic()+TIMEOUT
            while not ready.exists():
                assert time.monotonic()<until
                time.sleep(.005)
            pid=int(ready.read_text()); os.kill(pid,0)
            start=time.monotonic(); w.send(dict(op='exit'))
            w.p.wait(timeout=TIMEOUT)
            if isolated:
                assert w.messages.get(timeout=.5) is None
                os.kill(pid,0)
                record(test='control_eof_while_process_run_child_alive', seconds=time.monotonic()-start, child_alive=True, result='pass')
            else:
                try: early=w.messages.get(timeout=.2)
                except queue.Empty: early='held'
                assert early=='held', early
                assert w.messages.get(timeout=TIMEOUT) is None
                record(test='negative_control_inheritable', eof_held_seconds=time.monotonic()-start,result='pass')
            # All helper processes finish naturally within their three-second sleep.
            time.sleep(max(0,3.1-(time.monotonic()-start)))
        finally: w.close()
def streams(binary):
    w=Worker(binary)
    try:
        nonce=secrets.token_hex(32); scanners={}; threads=[]
        for name,pipe in [('stdout',w.p.stdout),('stderr',w.p.stderr)]:
            marker=f'\x1eRNX-WORKER-1:1:{name}:{nonce}\x1f'.encode()
            s=Scanner(marker,('worker',1,name)); scanners[name]=s
            def collect(pipe=pipe,s=s):
                while not s.ended:
                    b=os.read(pipe.fileno(),8192)
                    if not b: s.eof(); return
                    s.feed(b)
            t=threading.Thread(target=collect,daemon=True);t.start();threads.append(t)
        w.send(dict(op='emit',id=1,nonce=nonce))
        assert w.messages.get(timeout=TIMEOUT)==dict(type='settled',id=1)
        for t in threads: t.join(TIMEOUT); assert not t.is_alive()
        for name,s in scanners.items():
            assert s.ended and len(s.data)==CAP and s.discarded>0
            assert len(s.pending)==0
        # Delayed handoff retains collector identity; no ack until handoff.
        time.sleep(.05)
        assert all(s.identity[1]==1 for s in scanners.values())
        assert w.messages.empty()
        record(test='concurrent_streams', retained={n:len(s.data) for n,s in scanners.items()}, discarded={n:s.discarded for n,s in scanners.items()}, delayed_handoff_identity=1,result='pass')
        w.send(dict(op='ack',id=1))
        w.send(dict(op='shutdown',id=2,nonce=secrets.token_hex(32)))
        assert w.p.wait(timeout=TIMEOUT)==0
    finally:w.close()
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--rnx',type=pathlib.Path,required=True)
    args=parser.parse_args();binary=pathlib.Path(__file__).parent/'target/debug/worker-boundary-probe'
    record(platform=os.name, python=os.sys.version, rnx=str(args.rnx))
    scanner_tests(); isolation(binary,args.rnx,False);isolation(binary,args.rnx,True);streams(binary)
