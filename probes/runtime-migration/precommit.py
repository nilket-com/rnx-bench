"""Old-selection refusal preserves a started request and session bindings."""
from pathlib import Path
import json,os,sys,subprocess as sp,socket,threading,time,importlib.util
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target/matrix';O=B/'results/runtime-migration-0065';T=R/'tools/project/target/debug/rnx-project';OLD=B/'probes/native-inventory/target/stock/tools/project/target/release/rnx-project';S=B/'probes/native-inventory/target/fixed-rnx';store=W/"data space'quote/rnx/runtimes";old=json.loads((O/'old-installation.json').read_text());saved=(store/'current.json').read_bytes()
E={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','GIT_','CARGO_','RUST'))};E.update(XDG_DATA_HOME=str(W/"data space'quote"),XDG_STATE_HOME=str(W/'precommit-state'),RNX_PROJECT_TOOL=str(T),RNX_PROJECT_CACHE=str(W/'precommit-cache'),RNX_CONFIG=str(W/'absent'),RNX_HISTORY=str(W/'precommit-history'),TERM='xterm-256color')
spec=importlib.util.spec_from_file_location('term',B/'probes/project-interactive/common.py');term=importlib.util.module_from_spec(spec);spec.loader.exec_module(term)
sp.run([OLD,'runtime','select',old['id']],env=E,check=True,capture_output=True)
listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();accepted=threading.Event();release=threading.Event();errors=[]
def server():
 try:
  listener.settimeout(20);conn,_=listener.accept()
  with conn:
   conn.settimeout(20);data=b''
   while b'\r\n\r\n' not in data:data+=conn.recv(4096)
   accepted.set();assert release.wait(30);conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n73')
 except BaseException as e:errors.append(repr(e))
th=threading.Thread(target=server);th.start();t=term.Terminal([S,'--no-splash','--color=never'],W,E)
try:
 t.read();t.send(f'let held = 42; let q = http::get("http://127.0.0.1:{listener.getsockname()[1]}/");');t.send('let timer = time::sleep(20); select { _ = q => (), _ = timer => () };');assert accepted.wait(5)
 os.write(t.master,b':dep --offline polars\n');out=t.read();assert 'format 1' in out and 'runtime install --from' in out and 'Continue?' not in out,out
 assert '42' in t.send('held');release.set();assert '73' in t.send('q.await');assert not Path(E['XDG_STATE_HOME']).exists() and not Path(E['RNX_PROJECT_CACHE']).exists()
 os.write(t.master,b':q\n');t.read(False);assert t.p.wait(timeout=10)==0
 (O/'old-selection-precommit.pty').write_bytes(t.log);(O/'precommit.json').write_text(json.dumps(dict(started_request_retained=True,original_value=73,binding_retained=True,no_consent_or_scratch=True),indent=2)+'\n')
finally:
 release.set();t.close();th.join(10);listener.close();(store/'current.json').write_bytes(saved)
assert not th.is_alive() and not errors,errors
print('PASS old-selection refusal preserves started HTTP future')
