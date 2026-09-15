import sys,queue
from common import *
sys.path.insert(0,str(ROOT/'probes/jupyter-supervision'))
import probe
probe.OUT=OUT
from probe import Kernel,result
k=Kernel()
try:
    active=k.client.execute('time::sleep(10000).await?')
    while True:
        m=k.client.get_iopub_msg(timeout=5)
        if m['parent_header'].get('msg_id')==active and m['msg_type']=='status':break
    ids=[]
    for channel in [k.client.shell_channel,k.client.control_channel]:
        msg=k.client.session.msg('kernel_info_request');ids.append(msg['header']['msg_id']);channel.send(msg)
    assert k.client.get_control_msg(timeout=5)['msg_type']=='kernel_info_reply'
    try:k.client.get_shell_msg(timeout=.25);raise AssertionError('shell info bypassed execution')
    except queue.Empty:pass
    while True:
        try:m=k.client.get_iopub_msg(timeout=.05)
        except queue.Empty:break
        assert not(m['msg_type']=='status' and m['content']['execution_state']=='idle'),m
    k.control('interrupt_request');assert k.reply(active)['content']['ename']=='Interrupted'
    assert k.reply(ids[0])['msg_type']=='kernel_info_reply'
    assert result(k.execute('42')[1])=='42'
    log('shell_kernel_info_waits_control_stays_immediate',passed=True)
finally:k.close()

# Deliberately delay IOPub subscription: shell must not race its idle into a void.
from jupyter_client import BlockingKernelClient
from jupyter_client.connect import write_connection_file
e=Environment();p=None
try:
    connection=e.root/'connection.json';write_connection_file(str(connection),ip='127.0.0.1',key=b'fixture-key')
    p=subprocess.Popen([str(e.kernel),'--connection-file',str(connection),'--rnx',str(e.worker)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,env=e.env)
    client=BlockingKernelClient(connection_file=str(connection));client.load_connection_file()
    client.start_channels(shell=True,iopub=False,stdin=False,hb=False,control=True)
    id=client.kernel_info()
    try:client.get_shell_msg(timeout=.25);raise AssertionError('kernel info beat subscription')
    except queue.Empty:pass
    client.iopub_channel.start()
    reply=client.get_shell_msg(timeout=3);assert reply['parent_header']['msg_id']==id
    statuses=[]
    while statuses!=['busy','idle']:
        msg=client.get_iopub_msg(timeout=3)
        if msg['parent_header'].get('msg_id')==id and msg['msg_type']=='status':statuses.append(msg['content']['execution_state'])
    client.shutdown();reply=client.get_control_msg(timeout=5);assert reply['msg_type']=='shutdown_reply'
    p.wait(timeout=5.5);assert p.returncode==0
    client.stop_channels();log('delayed_subscription_gets_kernel_info_idle',passed=True)
finally:
    if p:
        if p.poll() is None:p.terminate();p.wait(timeout=6)
        p.stderr.close()
    e.close()
