#!/usr/bin/env python3
"""Real Jupyter clients over the owned transport and real 0046 worker. Linux."""
import json, os, pathlib, queue, signal, subprocess, tempfile, time
from jupyter_client import BlockingKernelClient
from jupyter_client.connect import write_connection_file
ROOT=pathlib.Path(__file__).resolve().parents[2]
BIN=ROOT.parent/'rnx/jupyter/target/release/rnx-jupyter'
WORKER=ROOT.parent/'rnx/target/release/rnx'
OUT=pathlib.Path(os.environ.get('RNX_JUPYTER_RESULTS',str(ROOT/'results/jupyter-0047-supervision')))
OUT.mkdir(exist_ok=True)

def log(case,**kw):print(json.dumps(dict(case=case,**kw)),flush=True)

class Kernel:
    def __init__(self,worker=WORKER,env=None):
        self.temp=tempfile.TemporaryDirectory(prefix='rnx notebook ')
        directory=pathlib.Path(self.temp.name)/'config-files';directory.mkdir()
        self.path=directory/'connection.json'
        write_connection_file(str(self.path),ip='127.0.0.1',key=b'fixture-only-key')
        self.errors=open(OUT/'kernel-stderr.txt','a')
        self.p=subprocess.Popen([str(BIN),'--connection-file',str(self.path),'--rnx',str(worker)],cwd=self.temp.name,stderr=self.errors,stdout=subprocess.DEVNULL,env=env)
        self.client=BlockingKernelClient(connection_file=str(self.path));self.client.load_connection_file();self.client.start_channels()
        self.client.wait_for_ready(timeout=10)
        self.replies={}
    def reply(self,id,timeout=10):
        end=time.monotonic()+timeout
        while id not in self.replies:
            msg=self.client.get_shell_msg(timeout=max(.01,end-time.monotonic()))
            self.replies[msg['parent_header']['msg_id']]=msg
        return self.replies.pop(id)
    def collect(self,id,timeout=10):
        messages=[];end=time.monotonic()+timeout
        while True:
            msg=self.client.get_iopub_msg(timeout=max(.01,end-time.monotonic()))
            if msg['parent_header'].get('msg_id')!=id:continue
            messages.append(msg)
            if msg['msg_type']=='status' and msg['content']['execution_state']=='idle':break
        reply=self.reply(id)
        assert messages[0]['content'].get('execution_state')=='busy'
        assert all(m['parent_header']==reply['parent_header'] for m in messages)
        return reply,messages
    def execute(self,source,**kw):return self.collect(self.client.execute(source,**kw))
    def control(self,kind,content={}):
        msg=self.client.session.msg(kind,content=content);self.client.control_channel.send(msg)
        r=self.client.get_control_msg(timeout=5);assert r['parent_header']['msg_id']==msg['header']['msg_id'];return r
    def close(self,restart=False):
        if self.p.poll() is None:
            r=self.control('shutdown_request',dict(restart=restart));assert r['content']['restart']==restart
            self.p.wait(timeout=5.5);assert self.p.returncode==0,self.p.returncode
        self.client.stop_channels();self.errors.close();self.temp.cleanup()

def result(messages):return next(m['content']['data']['text/plain'] for m in messages if m['msg_type']=='execute_result')
def streams(messages,name):return ''.join(m['content']['text'] for m in messages if m['msg_type']=='stream' and m['content']['name']==name)

def ordinary():
    k=Kernel()
    try:
        r,m=k.execute('let x = 40;');assert r['content']['status']=='ok' and not any(x['msg_type']=='execute_result' for x in m)
        r,m=k.execute('x + 2');assert result(m)=='42' and r['content']['execution_count']==2
        r,m=k.execute('print!("no newline"); io::eprint("err\\0tail")?; 7');assert result(m)=='7' and streams(m,'stdout')=='no newline' and streams(m,'stderr')=='err\0tail'
        assert next(i for i,x in enumerate(m) if x['msg_type']=='execute_result')<len(m)-1
        r,m=k.execute('1.missing()');assert r['content']['ename']=='RuntimeError';assert 'missing' in r['content']['evalue']
        r,m=k.execute('this is broken');assert r['content']['ename']=='CompileError'
        r,m=k.execute('x');assert result(m)=='40'
        r,m=k.execute('fs::cwd()?');assert json.loads(result(m))==k.temp.name
        old=r['content']['execution_count']
        r,m=k.execute('let hidden = 3; print!("silent");',silent=True);assert r['content']['execution_count']==old and all(x['msg_type']=='status' for x in m)
        r,m=k.execute('',silent=True);assert r['content']['execution_count']==old
        r,m=k.execute('hidden',store_history=False,user_expressions={'u':'hidden'});assert result(m)=='3' and r['content']['execution_count']==old and r['content']['user_expressions']['u']['ename']=='UnsupportedFeature'
        r,m=k.execute('let old = |v| v.earlier_missing();');defined=r['content']['execution_count']
        r,m=k.execute('old(1)');assert r['metadata']['rnx']['notebook_count']==defined,r
        r,m=k.execute('let old = |v| v.second_missing();');defined=r['content']['execution_count']
        r,m=k.execute('old(1)');assert 'second_missing' in r['content']['evalue'] and r['metadata']['rnx']['notebook_count']==defined
        r,m=k.execute('x'*32769);assert r['content']['ename']=='Refused'
        r,m=k.execute('\0'*170000);assert r['content']['ename']=='Refused'
        assert not any(x['msg_type']=='execute_input' for x in m)
        r,m=k.execute(':reset');assert r['content']['status']=='error'
        r,m=k.execute('x');assert result(m)=='40'
        log('persistent_values_errors_streams_counts_and_origins',passed=True)
    finally:k.close()

def interrupts():
    k=Kernel()
    try:
        for source in ['loop {}','time::sleep(10000).await?','process::run("/bin/sleep", ["10"], #{})?']:
            id=k.client.execute(source)
            # Busy proves scheduling began; the signal may still race armed.
            while True:
                m=k.client.get_iopub_msg(timeout=5)
                if m['parent_header'].get('msg_id')==id and m['msg_type']=='status':break
            start=time.monotonic();assert k.control('interrupt_request')['content']['status']=='ok'
            messages=[]
            while True:
                m=k.client.get_iopub_msg(timeout=5)
                if m['parent_header'].get('msg_id')!=id:continue
                messages.append(m)
                if m['msg_type']=='status' and m['content']['execution_state']=='idle':break
            r=k.reply(id);assert r['content']['ename']=='Interrupted',r
            elapsed=time.monotonic()-start;assert elapsed<1,elapsed
            assert result(k.execute('42')[1])=='42'
            log('interrupt_recovery',source=source,seconds=elapsed)
        id=k.client.execute('time::sleep(10000).await?');time.sleep(.1)
        start=time.monotonic();k.control('kernel_info_request');assert time.monotonic()-start<.5
        k.close(restart=True);log('active_shutdown_and_independent_control',passed=True)
    finally:
        if k.p.poll() is None:k.close()

def queued():
    k=Kernel()
    try:
        ids=[k.client.execute('time::sleep(300).await?; 1.missing()',stop_on_error=True)]
        ids += [k.client.execute('let should_not_run = 1;') for _ in range(4)]
        r=k.reply(ids[0]);count=r['content']['execution_count'];assert r['content']['status']=='error'
        for id in ids[1:]:r=k.reply(id);assert r['content']['ename']=='ExecutionAborted' and r['content']['execution_count']==count
        r,m=k.execute('should_not_run');assert r['content']['status']=='error'
        first=k.client.execute('time::sleep(200).await?; 1.missing()',stop_on_error=False)
        second=k.client.execute('5');assert k.reply(first)['content']['status']=='error';assert k.reply(second)['content']['status']=='ok'
        log('stop_on_error_snapshot_and_continue',passed=True)
    finally:k.close()

def fresh_restart():
    first=Kernel()
    r,m=first.execute('let before_restart = 7;')
    session=r['header']['session']
    first.close(restart=True)
    second=Kernel()
    try:
        r,m=second.execute('before_restart')
        assert r['content']['status']=='error' and r['content']['execution_count']==1
        assert r['header']['session']!=session
        log('manager_starts_fresh_kernel_after_restart',passed=True)
    finally:second.close()

if __name__=='__main__':
    ordinary();interrupts();queued();fresh_restart()
