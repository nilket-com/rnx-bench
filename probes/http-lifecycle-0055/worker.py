#!/usr/bin/env python3
"""Stock worker HTTP scope policies; observe before issuing any next input."""
import json, os, pathlib, signal, socket, sys, threading, time
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT.parent/'rnx/tests'))
from worker_parent import Parent
OUT=ROOT/'results/http-lifecycle-0055'; OUT.mkdir(exist_ok=True,parents=True)
BIN=ROOT.parent/'rnx/target/release/rnx'
class Held:
    def __init__(self):
        self.listener=socket.socket();self.listener.bind(('127.0.0.1',0));self.listener.listen();self.listener.settimeout(5)
        self.url='http://127.0.0.1:%s/'%self.listener.getsockname()[1]
        self.seen=threading.Event();self.release=threading.Event();self.closed=threading.Event();self.error=None
        def serve():
            try:
                with self.listener:
                    conn,_=self.listener.accept()
                    with conn:
                        conn.settimeout(5);data=b''
                        while not data.endswith(b'\r\n\r\n'):
                            piece=conn.recv(1);assert piece;data+=piece
                        self.seen.set();conn.settimeout(.01)
                        end=time.monotonic()+10
                        while time.monotonic()<end:
                            if self.release.is_set():
                                conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok');return
                            try:
                                piece=conn.recv(1)
                                assert piece==b'',piece
                                self.closed.set();return
                            except socket.timeout: pass
                        raise AssertionError('held fixture timeout')
            except BaseException as e:self.error=repr(e)
        self.thread=threading.Thread(target=serve);self.thread.start()
results={}
env={k:v for k,v in os.environ.items() if k.lower() not in ['http_proxy','https_proxy','all_proxy','no_proxy'] and not k.startswith('RNX_')}
env.update(TERM='xterm',RNX_CONFIG='/nonexistent-0055-config',RNX_MEMORY_CEILING='67108864')
for case in ['unrelated-interrupt','touched-interrupt','reset','shutdown','caught-error']:
    f=Held();w=Parent(str(BIN),env)
    try:
        assert w.execute('let q = http::get('+json.dumps(f.url)+');')[0]['failure'] is None
        assert w.execute('select { _ = q => (), _ = time::sleep(30) => () };')[0]['failure'] is None
        assert f.seen.wait(2) and not f.closed.is_set()
        if case.endswith('interrupt'):
            code='time::sleep(120000).await?' if case.startswith('unrelated') else 'select { _ = q => (), _ = time::sleep(120000) => () };'
            w.begin(code);assert w.message()['type']=='armed';time.sleep(.03);w.p.send_signal(signal.SIGINT)
            reply,_=w.settled();assert reply['failure']['category']=='interrupted',reply
            assert not reply['state_lost'];w.handoff()
            if case.startswith('unrelated'):
                assert not f.closed.is_set();f.release.set()
                answer=w.execute('q.await?.body')[0];assert answer['text_plain']=='"ok"',answer
            else:
                answer=w.execute('q.await')[0];assert answer['text_plain']=='Err("operation cancelled")',answer
                w.execute('time::sleep(30).await?');assert f.closed.wait(.5)
        elif case=='caught-error':
            reply=w.execute('match http::get("bad url").await { Ok(_) => false, Err(_) => true }')[0]
            assert reply['text_plain']=='true',reply
            assert not f.closed.is_set();f.release.set()
            assert w.execute('q.await?.body')[0]['text_plain']=='"ok"'
        else:
            w.begin(op=case);reply,_=w.settled();assert reply['failure'] is None and not reply['state_lost'],reply
            if case=='shutdown':
                assert f.closed.wait(.5);w.handoff();assert w.p.wait(timeout=2)==0
            else:
                # Reset is logical. No EOF asserted while parked before ack.
                reply['closed_while_parked_observation']=f.closed.is_set()
                w.handoff();assert w.execute('42')[0]['text_plain']=='42'
                w.execute('time::sleep(30).await?');assert f.closed.wait(.5)
        results[case]=reply
    finally:
        w.close();f.release.set();f.thread.join(timeout=6)
        assert not f.thread.is_alive() and f.error is None,f.error
(OUT/'worker.json').write_text(json.dumps(results,indent=2)+'\n')
print('stock worker unrelated/touched interrupts, caught error, reset reuse and shutdown passed')
