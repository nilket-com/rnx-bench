#!/usr/bin/env python3
import json,os,pathlib,queue,subprocess,tempfile,time
from probe import Kernel,ROOT,OUT,log
FAKE=ROOT/'probes/jupyter-supervision/fake-worker.py'
EXAMPLE=ROOT.parent/'rnx/jupyter/target/release/examples/worker-probe'
for phase,mode in [('stream','settled'),('result','settled'),('result','repeat')]:
    with tempfile.TemporaryDirectory() as d:
        trace=pathlib.Path(d)/'ack'
        env=os.environ.copy();env['RNX_FAKE_TRACE']=str(trace);env['RNX_FAKE_MODE']=mode
        p=subprocess.run([str(EXAMPLE),str(FAKE),phase],env=env,capture_output=True,text=True,timeout=12)
        assert p.returncode==0,(p.stdout,p.stderr)
        assert not trace.exists(),'a blocked handoff was acknowledged'
        measurement=json.loads(p.stdout);measurement['mode']=mode;print(json.dumps(measurement),flush=True)
for mode in ['partial','malformed']:
    with tempfile.TemporaryDirectory() as d:
        env=os.environ.copy();env['RNX_FAKE_MODE']=mode;env['RNX_FAKE_TRACE']=str(pathlib.Path(d)/'ack')
        k=Kernel(worker=FAKE,env=env)
        id=k.client.execute('42')
        r=k.reply(id);assert r['content']['ename']=='WorkerDied',r
        k.p.wait(timeout=5.5);assert k.p.returncode!=0
        messages=[]
        while True:
            try:m=k.client.get_iopub_msg(timeout=.15)
            except queue.Empty:break
            if m['parent_header'].get('msg_id')==id:messages.append(m)
        assert not any(m['msg_type']=='execute_result' or (m['msg_type']=='status' and m['content']['execution_state']=='idle') for m in messages)
        assert not pathlib.Path(env['RNX_FAKE_TRACE']).exists()
        k.client.stop_channels();k.errors.close();k.temp.cleanup()
        log('incomplete_boundary_no_success_or_ack',mode=mode,passed=True)
