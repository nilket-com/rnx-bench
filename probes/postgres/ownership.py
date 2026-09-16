"""Drive ownership only through Rune in the real rnx worker, no adapter tasks."""
import json,os,pathlib,signal,subprocess,sys,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT.parent/'rnx/tests'))
from worker_parent import Parent
BIN=ROOT/'probes/postgres/ownership/target/release/rnx-postgres-ownership'
PG=pathlib.Path('/usr/lib/postgresql/18/bin')
OUT=pathlib.Path(os.environ.get('RNX_PG_OWNERSHIP_OUT', str(ROOT/'results/lifecycle-0053/postgres')));OUT.mkdir(exist_ok=True,parents=True)
results={}
def sockets(pid):
    result={}
    for p in pathlib.Path(f'/proc/{pid}/fd').iterdir():
        try:target=os.readlink(p)
        except FileNotFoundError:continue
        if target.startswith('socket:['):result[p.name]=target
    return result
with tempfile.TemporaryDirectory(prefix='rnx-pg-ownership-') as directory:
    directory=pathlib.Path(directory);data=directory/'data'
    def pg(args,check=True):return subprocess.run([str(PG/args[0]),*map(str,args[1:])],capture_output=True,text=True,check=check,timeout=15)
    pg(['initdb','-D',data,'--auth=trust','--no-locale'])
    try:
        pg(['pg_ctl','-D',data,'-l',directory/'server.log','-o',f"-c listen_addresses='' -c unix_socket_directories='{directory}'",'-w','start'])
        postmaster=int((data/'postmaster.pid').read_text().splitlines()[0])
        def activity(tag):
            return pg(['psql','-XAt','-h',directory,'-d','postgres','-c',f"SELECT pid, state, query FROM pg_stat_activity WHERE application_name='{tag}'"]).stdout.strip()
        for case in ['success','deadline','conversion','interrupt','pending-drop','budget','lazy','retained-interrupt']:
            trace=directory/(case+'.trace')
            env=dict(os.environ,TERM='xterm',RNX_CONFIG=str(directory/'absent'),RNX_HISTORY=str(directory/'history'),RNX_PG_PROBE_TRACE=str(trace))
            tag='rnx-pg-ownership-'+case
            url=f'postgresql:///postgres?host={directory}&application_name={tag}'
            def call(seconds=120,ms=90000,refuse=False):return f'pg_probe::query({json.dumps(url)}, {float(seconds)}, {ms}, {str(refuse).lower()})'
            if case=='success':source=call(.5)+'.await?'
            elif case=='conversion':source=call(.5,refuse=True)+'.await'
            elif case=='deadline':source='match '+call(5,600)+'.await { Ok(n) => n.to_string(), Err(e) => e }'
            elif case=='interrupt':source=call()+'.await?'
            elif case=='lazy':source='let q = '+call()+';'
            elif case=='retained-interrupt':source='let timer = time::sleep(120000); select { _ = q => (), _ = timer => () };'
            else:
                ending='panic!("discard new binding")' if case=='pending-drop' else 'loop {}'
                source='let q = '+call()+'; let timer = time::sleep(400); select { _ = q => (), _ = timer => () }; io::eprint("released-select........................................................................................................................................................................................................")?; time::sleep(600).await?; '+ending
            w=Parent(str(BIN),env)
            try:
                if case=='retained-interrupt':
                    declared=w.execute('let q = '+call(5,600)+';')[0]
                    assert declared['failure'] is None,declared
                before=sockets(w.p.pid);start=time.monotonic();w.begin(source)
                armed=w.message(timeout=5);assert armed['type']=='armed',armed
                observed=None;released=None;active=None
                if case!='lazy':
                    limit=time.monotonic()+4
                    while time.monotonic()<limit:
                        now=sockets(w.p.pid)
                        if len(now)>len(before):
                            observed=now;active=activity(tag)
                            if 'active' in active and 'pg_sleep' in active:break
                        if not w.messages.empty():break
                        time.sleep(.005)
                    assert observed is not None and active and 'active' in active,(case,observed,active)
                    if case in ['interrupt','retained-interrupt']:w.p.send_signal(signal.SIGINT)
                    if case in ['pending-drop','budget']:
                        while time.monotonic()<limit:
                            with w.lock:seen=b'released-select' in w.streams['stderr'].data
                            if seen:
                                released=sockets(w.p.pid);assert len(released)>len(before),(case,released,trace.read_text() if trace.exists() else '')
                                break
                            if not w.messages.empty():break
                            time.sleep(.005)
                        assert released is not None,(case,'select marker not observed')
                reply,messages=w.settled()
                after=sockets(w.p.pid)
                # Check while worker is parked awaiting ack: no subsequent input.
                events=trace.read_text() if trace.exists() else ''
                entry=dict(setup_source=('let q = '+call(5,600)+';') if case=='retained-interrupt' else None,source=source,before=before,opened=observed,active=active,after_select=released,after=after,reply=reply,seconds=time.monotonic()-start,events=events,backend_after=activity(tag))
                results[case]=entry
                (OUT/'ownership.json').write_text(json.dumps(results,indent=2)+'\n')
                if case=='retained-interrupt':
                    entry['ownership_passed']=len(after)==len(before)
                    assert entry['ownership_passed'],entry
                    time.sleep(.8)  # Parent waits; the worker receives no input or ack.
                    entry['after_passive_wait']=sockets(w.p.pid)
                    entry['backend_after_passive_wait']=activity(tag)
                    entry['events_after_passive_wait']=trace.read_text()
                    (OUT/'ownership.json').write_text(json.dumps(results,indent=2)+'\n')
                    w.handoff()
                    entry['repoll']=w.execute('q.await')[0]
                    assert entry['repoll']['text_plain']=='Err(\"operation cancelled\")',entry
                    assert len(sockets(w.p.pid))==len(before),entry
                    (OUT/'ownership.json').write_text(json.dumps(results,indent=2)+'\n')
                    print(case, 'socket count',len(before),'->',len(after),flush=True)
                    continue
                assert len(after)==len(before),(case,entry)
                if case=='lazy':assert not events and not entry['backend_after'],entry
                else:
                    assert events.startswith('connected 0 '),events
                    assert events.rstrip().endswith(f'dropped 0 {len(before)}'),events
                if case=='success':assert reply['text_plain']=='42',reply
                if case=='interrupt':assert reply['failure']['category']=='interrupted',reply
                if case=='pending-drop':assert 'discard new binding' in str(reply),reply
                if case=='budget':assert 'budget' in str(reply).lower(),reply
                w.handoff()
                if case in ['pending-drop','budget']:
                    missing=w.execute('q')[0]
                    assert missing['failure'] is not None and 'No local variable `q`' in str(missing),missing
                    entry['binding_unpublished']=missing
                    (OUT/'ownership.json').write_text(json.dumps(results,indent=2)+'\n')
                print(case,'passed',round(entry['seconds'],3),flush=True)
            finally:w.close()
    finally:
        stopped=pg(['pg_ctl','-D',data,'stop','-m','fast','-w'],check=False)
        assert stopped.returncode==0,stopped
        assert not pathlib.Path(f'/proc/{postmaster}').exists(),postmaster
(OUT/'ownership-cleanup.json').write_text(json.dumps({'directory':str(directory),'directory_removed':not directory.exists(),'postmaster':postmaster,'postmaster_exited':not pathlib.Path(f'/proc/{postmaster}').exists(),'stop_output':stopped.stdout},indent=2)+'\n')
print('seven required cases and retained-binding cancellation passed; private cluster stopped and removed')
if any(r.get('ownership_passed') is False for r in results.values()):
    print('STOP: retained future still owns its socket after interruption')
    sys.exit(2)
