#!/usr/bin/env python3
import json,os,pathlib,queue,signal,sys,time
from probe import Kernel,ROOT,OUT,log,result,streams

def stream_cases():
    k=Kernel()
    try:
        id=k.client.execute('println("progress"); time::sleep(500).await?; 8')
        start=time.monotonic();seen=[]
        while True:
            msg=k.client.get_iopub_msg(timeout=5)
            if msg['parent_header'].get('msg_id')!=id:continue
            seen.append(msg)
            if msg['msg_type']=='stream':
                assert msg['content']['text']=='progress\n';assert time.monotonic()-start<.4;break
        while True:
            msg=k.client.get_iopub_msg(timeout=5)
            if msg['parent_header'].get('msg_id')!=id:continue
            seen.append(msg)
            if msg['msg_type']=='status' and msg['content']['execution_state']=='idle':break
        assert k.reply(id)['content']['status']=='ok' and result(seen)=='8'
        r,m=k.execute(r'fs::write("/dev/stdout", b"\xf0\x9f")?; time::sleep(20).await?; fs::write("/dev/stdout", b"\x98\x80\xff\xc3")?; 4')
        assert r['content']['status']=='ok',r
        assert streams(m,'stdout')=='😀��',streams(m,'stdout')
        assert any(x['metadata'].get('rnx',{}).get('utf8_replaced') for x in m)
        text='x'*8192
        r,m=k.execute('for n in 0..300 { print!("'+text+'"); host::eprint("'+text+'")?; }')
        for name in ['stdout','stderr']:
            output=streams(m,name);assert output.startswith('x'*(2*1024*1024))
            assert '360448 bytes discarded' in output,(name,len(output),output[-200:])
        assert result(k.execute('42')[1])=='42'
        log('progress_utf8_and_both_caps',passed=True)
    finally:k.close()

def admission():
    for amount,source,refused in [(70,'1',6),(6,'x'*900000,2),(6,'\0'*140000,2)]:
        k=Kernel()
        try:
            active=k.client.execute('time::sleep(10000).await?')
            while True:
                m=k.client.get_iopub_msg(timeout=5)
                if m['parent_header'].get('msg_id')==active and m['msg_type']=='status':break
            ids=[k.client.execute(source) for _ in range(amount)]
            bad=[]
            for _ in range(refused):
                r=k.client.get_shell_msg(timeout=8);assert r['content']['ename']=='KernelBusy',r
                bad.append(r['parent_header']['msg_id'])
            k.control('interrupt_request');assert k.reply(active)['content']['ename']=='Interrupted'
            for id in ids:
                if id not in bad:assert k.reply(id)['content']['ename']=='ExecutionAborted'
            assert result(k.execute('6')[1])=='6'
            log('execution_admission',requests=amount,source_bytes=len(source),refused=len(bad))
        finally:k.close()

def descendants(mode):
    k=Kernel()
    try:
        ready=pathlib.Path(k.temp.name)/'descendant.json'
        script=ROOT/'probes/jupyter-containment-replacement/descendant.py'
        source=f'process::run({json.dumps(sys.executable)}, [{json.dumps(str(script))}, {json.dumps(str(ready))}], #{{timeout_ms: 90000}})?'
        id=k.client.execute(source)
        end=time.monotonic()+5
        while not ready.exists():assert time.monotonic()<end;time.sleep(.01)
        pid=json.loads(ready.read_text())['pid'];assert pathlib.Path(f'/proc/{pid}').exists()
        # Discover the worker separately; the kernel receives neither PID.
        worker=int(pathlib.Path(f'/proc/{k.p.pid}/task/{k.p.pid}/children').read_text().split()[0]) if pathlib.Path(f'/proc/{k.p.pid}/task/{k.p.pid}/children').read_text().split() else None
        if worker is None:
            children=[]
            for task in pathlib.Path(f'/proc/{k.p.pid}/task').iterdir():children+=list(map(int,(task/'children').read_text().split()))
            worker=children[0]
        start=time.monotonic()
        if mode=='shutdown':k.close()
        else:
            os.kill(worker,signal.SIGKILL);k.p.wait(timeout=5.5);assert k.p.returncode!=0
            # An incomplete worker boundary must not fabricate a successful idle.
            r=k.reply(id);assert r['content']['ename']=='WorkerDied'
            k.client.stop_channels();k.errors.close();k.temp.cleanup()
        assert not pathlib.Path(f'/proc/{pid}').exists(),pid
        log('descendant_cleanup',mode=mode,seconds=time.monotonic()-start)
    finally:
        if k.p.poll() is None:k.close()

def async_cpu_shutdown():
    k=Kernel()
    try:
        id=k.client.execute('time::sleep(0).await?; println("entered"); loop {}')
        while True:
            msg=k.client.get_iopub_msg(timeout=5)
            if msg['parent_header'].get('msg_id')==id and msg['msg_type']=='stream':break
        k.control('interrupt_request')
        end=time.monotonic()+.15
        while time.monotonic()<end:
            try:reply=k.client.get_shell_msg(timeout=end-time.monotonic())
            except queue.Empty:break
            assert reply['parent_header'].get('msg_id')!=id,reply
        assert k.p.poll() is None
        start=time.monotonic();k.close(restart=True);assert time.monotonic()-start<5.5
        log('async_cpu_requires_hard_shutdown',seconds=time.monotonic()-start)
    finally:
        if k.p.poll() is None:k.close()

if __name__=='__main__':
    stream_cases();admission();descendants('shutdown');descendants('worker_death');async_cpu_shutdown()
