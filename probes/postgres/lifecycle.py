"""Real adapter through Rune; observe descriptors before acknowledgement."""
import json, os, pathlib, signal, subprocess, sys, time
from cluster import Cluster
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT.parent/'rnx/tests'))
from worker_parent import Parent
BIN = ROOT.parent/'rnx/adapters/postgres/target/release/rnx-pg'
TEST = BIN.with_name('rnx-pg-test')
OUT = ROOT/'results/postgres-0052-adapter'
OUT.mkdir(parents=True, exist_ok=True)
results = {}
def sockets(pid):
    found = {}
    for path in pathlib.Path(f'/proc/{pid}/fd').iterdir():
        try: link = os.readlink(path)
        except FileNotFoundError: continue
        if link.startswith('socket:['): found[path.name] = link
    return found
def save(): (OUT/'lifecycle.json').write_text(json.dumps(results, indent=2)+'\n')
with Cluster() as c:
    env = dict(os.environ, TERM='xterm', RNX_CONFIG=str(c.root/'absent'), RNX_HISTORY=str(c.root/'history'))
    def call(sql, ms=1000):
        return f'postgres::query({json.dumps(c.url.replace('rnx-pg-fixture', tag))}, {json.dumps(sql)}, [], #{{timeout_ms:{ms}}})'
    tag='rnx-pg-fixture'
    def activity():
        return c.sql("SELECT pid, state, query FROM pg_stat_activity WHERE application_name='"+tag+"'").stdout.strip()
    # The 90-second residual is observed separately, while the other cases run.
    for case in ['interrupt', 'success', 'deadline', 'decode', 'pending-drop', 'budget', 'lazy', 'retained']:
        tag='rnx-pg-fixture-'+case
        w = Parent(str(BIN), env)
        try:
            q = call('SELECT 1 AS n FROM pg_sleep(120)', 90000 if case=='interrupt' else 1500)
            if case=='retained':
                r=w.execute('let q = '+q+';')[0]; assert r['failure'] is None,r
            if case=='success': source=call('SELECT 42 AS n FROM pg_sleep(0.05)')+'.await?'
            elif case=='decode': source='match '+call("SELECT 'infinity'::timestamptz AS ts")+'.await { Ok(_) => "wrong", Err(e) => e }'
            elif case=='deadline': source='match '+call('SELECT 1 AS n FROM pg_sleep(5)', 200)+'.await { Ok(_) => "wrong", Err(e) => e }'
            elif case=='lazy': source='let q = '+q+';'
            elif case=='retained': source='let timer=time::sleep(120000); select { _ = q => (), _ = timer => () };'
            elif case in ['pending-drop','budget']:
                source='let q = '+q+'; let t=time::sleep(300); select { _=q=>(), _=t=>() }; io::eprint("unpolled-open'+'.'*220+'")?; time::sleep(400).await?; '+('panic!("discard")' if case=='pending-drop' else 'loop {}')
            else: source=q+'.await?'
            before=sockets(w.p.pid); start=time.monotonic(); w.begin(source); armed=w.message(); assert armed['type']=='armed',armed
            opened=None;active=None;unpolled=None;signal_at=None
            if case in ['interrupt','retained','pending-drop','budget','deadline']:
                deadline=time.monotonic()+5
                while time.monotonic()<deadline:
                    opened=sockets(w.p.pid); active=activity()
                    if len(opened)>len(before) and 'active' in active: break
                    time.sleep(.005)
                assert len(opened)>len(before) and 'active' in active,(case,opened,active)
                if case in ['interrupt','retained']:
                    w.p.send_signal(signal.SIGINT); signal_at=time.monotonic()
                elif case in ['pending-drop','budget']:
                    while time.monotonic()<deadline:
                        with w.lock: seen=b'unpolled-open' in w.streams['stderr'].data
                        if seen: break
                        time.sleep(.005)
                    assert seen
                    unpolled=sockets(w.p.pid); assert len(unpolled)>len(before)
            observed_active_at=time.monotonic() if active else None
            reply,messages=w.settled(); after=sockets(w.p.pid)
            assert len(after)==len(before),(case,before,after,reply)
            if case in ['interrupt','retained']: assert reply['failure']['category']=='interrupted',reply
            elif case=='budget': assert 'budget' in str(reply),reply
            elif case=='pending-drop': assert 'discard' in str(reply),reply
            else: assert reply['failure'] is None,reply
            results[case]=dict(after_signal_seconds=time.monotonic()-signal_at if signal_at else None,before=before,opened=opened,active=active,unpolled=unpolled,after=after,reply=reply,seconds=time.monotonic()-start)
            if case=='deadline':
                backend=int(active.split('|')[0])
                while c.sql(f'SELECT count(*) FROM pg_stat_activity WHERE pid={backend}').stdout.strip()!='0':
                    assert time.monotonic()-observed_active_at < .3
                    time.sleep(.005)
                results[case]['server_disappearance_after_observed_active']=time.monotonic()-observed_active_at
            if case=='interrupt':
                interrupt_start=start
                interrupted_backend=int(active.split('|')[0])
                results[case]['backend_after']=activity()
            w.handoff()
            if case=='retained':
                r=w.execute('match q.await { Ok(_) => "wrong", Err(e) => e }')[0]
                assert r['text_plain']=='"operation cancelled"',r
                assert len(sockets(w.p.pid))==len(before)
                results[case]['repoll']=r
            save(); print(case,'passed',flush=True)
        finally: w.close()
    tag='rnx-pg-fixture-reset'
    w=Parent(str(BIN),env)
    try:
        source='let q='+call('SELECT 1 AS n FROM pg_sleep(120)',1500)+'; let t=time::sleep(100); select { _=q=>(), _=t=>() };'
        reply=w.execute(source)[0]; assert reply['failure'] is None,reply
        pending=sockets(w.p.pid); assert pending and 'active' in activity(),pending
        w.begin(op='reset'); reply,_=w.settled()
        assert reply['failure'] is None and not sockets(w.p.pid),reply
        results['reset pending']=dict(before=pending,after=sockets(w.p.pid),reply=reply)
        w.handoff()
        reply=w.execute(call('SELECT 42 AS n')+'.await?')[0]
        assert reply['failure'] is None and '42' in reply['text_plain'],reply
    finally:w.close()
    # The monitor proves commit while the call still owns its socket, before
    # the test hook lets the infinity decoder refuse the returned value.
    tag='rnx-pg-fixture'
    c.sql('CREATE TABLE committed(ts timestamptz)')
    pause=c.root/'pause'
    w=Parent(str(TEST),dict(env,RNX_PG_TEST_PAUSE=str(pause)))
    try:
        w.begin('match '+call("INSERT INTO committed VALUES('infinity') RETURNING ts", 5000)+'.await { Ok(_) => "wrong", Err(e) => e }')
        assert w.message()['type']=='armed'
        deadline=time.monotonic()+4
        while not pause.with_suffix('.ready').exists() and time.monotonic()<deadline: time.sleep(.005)
        assert pause.with_suffix('.ready').exists()
        count=c.sql('SELECT count(*) FROM committed').stdout.strip(); assert count=='1',count
        assert sockets(w.p.pid), 'query already dropped before observation'
        pause.with_suffix('.release').write_text('continue')
        reply,_=w.settled(); assert 'infinite timestamptz' in str(reply),reply
        assert not sockets(w.p.pid)
        results['committed refusal']=dict(count_before_refusal=count,reply=reply)
        w.handoff()
    finally: w.close()
    # No input-storage growth: both sources are one input, one uses 100 calls.
    memory=[]
    for count in [1,100]:
        source='for _ in 0..'+str(count)+' { '+call('SELECT 1 AS n')+'.await?; }'
        p=subprocess.run([str(BIN)],input=source+'\n:memory\n:reset\n:q\n',env=env,text=True,capture_output=True,timeout=10)
        assert p.returncode==0 and not p.stderr,p
        memory.append(p.stdout)
    import re
    # Keep the exact memory report as evidence and parse the current field.
    live=[int(re.search(r'tracked live allocation request bytes: (\d+)', text).group(1)) for text in memory]
    assert abs(live[1]-live[0]) <= 64*1024,live
    results['memory']=dict(reports=memory,live_bytes=live,delta=live[1]-live[0],tolerance=64*1024)
    print('memory reports',memory,flush=True)
    # Measure the deliberately long backend lifetime independently of the
    # socket checks above. No lower bound is asserted.
    while True:
        active=c.sql(f'SELECT count(*) FROM pg_stat_activity WHERE pid={interrupted_backend}').stdout.strip()
        if active=='0': break
        assert time.monotonic()-interrupt_start < 90.5,active
        time.sleep(.03)
    results['interrupt']['backend_gone_seconds']=time.monotonic()-interrupt_start
    assert c.sql("SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE 'rnx-pg-fixture%'").stdout.strip()=='0'
    results['cleanup']=dict(directory=str(c.root),postmaster=c.postmaster)
    save()
print('adapter ownership, commitment and backend lifetime passed; private cluster removed')
