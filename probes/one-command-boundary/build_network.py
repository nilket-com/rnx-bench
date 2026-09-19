from common import *
s=json.loads((O/'setup.json').read_text())
ns=['bwrap','--unshare-user','--uid',str(os.getuid()),'--gid',str(os.getgid()),'--unshare-net','--bind','/','/','--dev','/dev','--proc','/proc','--']
trace=O/'stock-build-network.trace'
p=run(ns+['strace','-f','-e','trace=network','-o',trace,'cargo','install','--path',s['source'],'--offline','--locked','--root',T/'install-network-control','--target-dir',T/'build-target'],timeout=1200)
assert 'AF_INET' not in trace.read_text()
row=json.loads(run([T/'install-network-control/bin/rnx','--probe-coordinates']).stdout);assert row['state']=='unverified'
(O/'stock-build-network.stderr').write_bytes(p.stderr);save('stock-build-network.json',{'classification':row,'internet_socket_calls':0,'network_disabled':True,'trace':'stock-build-network.trace'})
print('Actual stock path installation has zero Internet socket calls',flush=True)
