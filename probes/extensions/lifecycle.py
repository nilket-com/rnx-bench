#!/usr/bin/env python3
"""Lifecycle at real CLI and parked-worker boundaries, using the external app."""
import json, os, pathlib, signal, subprocess, sys, tempfile, time
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT.parent/'rnx/tests'))
from worker_parent import Parent
BIN = ROOT/'probes/extensions/target/release/lifecycle'
OUT = ROOT/'results/lifecycle-0053'; OUT.mkdir(parents=True,exist_ok=True)
SELECT = 'let timer = time::sleep(5); select { _ = q => (), _ = timer => () };'
results = {}
with tempfile.TemporaryDirectory(prefix='rnx-lifecycle-') as tmp:
    env = dict(os.environ, TERM='xterm', RNX_CONFIG=tmp+'/absent', RNX_HISTORY=tmp+'/history')
    def run(args, source=None):
        p = subprocess.run([str(BIN), *args], input=source, capture_output=True, text=True, env=env, timeout=10)
        return dict(code=p.returncode, stdout=p.stdout, stderr=p.stderr)
    for mode in ['eval','run','session']:
        code = 'fixture::ready().await?'
        if mode=='run':
            f=pathlib.Path(tmp)/'main.rn'; f.write_text('pub async fn main(_) { '+code+' }'); r=run(['run',str(f)])
        elif mode=='eval': r=run(['eval',code])
        else:r=run([],code+'\n:q\n')
        assert r['code']==0 and '42' in r['stdout'],(mode,r)
        results[mode]=r
    r=run(['eval', 'let n=0; while n<1000 { fixture::ready().await?; n+=1; }; n'])
    assert r['stdout']=='1000\n' and r['code']==0,r
    results['one-input-1000-calls']=r
    for mode in ['eval','run','session']:
        code='let q = fixture::pending(true); '+SELECT+' panic!("stop");'
        if mode=='run':
            f=pathlib.Path(tmp)/'bad.rn';f.write_text('pub async fn main(_) { '+code+' }');r=run(['run',str(f)])
        elif mode=='eval':r=run(['eval',code])
        else:r=run([],code+'\n99\n')
        assert r['code']==1 and 'lifecycle cleanup panicked' in r['stderr'],(mode,r)
        assert 'thread \'main\' panicked' not in r['stderr'] and '99' not in r['stdout'],r
        results[mode+'-destructor']=r
    for ending in [':q\n', '']:
        r=run([], 'let q = fixture::pending(true); '+SELECT+'\n'+ending)
        assert r['code']==1 and r['stderr'].count('lifecycle cleanup panicked')==1,r
        results['quit-destructor' if ending else 'eof-destructor']=r
    for case in ['interrupt','runtime','reset','shutdown','destructor']:
        w=Parent(str(BIN),env)
        try:
            assert w.execute('let kept = 42; let q = fixture::pending('+str(case=='destructor').lower()+');')[0]['failure'] is None
            if case=='interrupt':
                w.begin('let timer = time::sleep(120000); select { _ = q => (), _ = timer => () };')
                assert w.message()['type']=='armed'
                time.sleep(.1)
                w.p.send_signal(signal.SIGINT)
            elif case in ['runtime','destructor']:
                if case=='destructor':
                    assert w.execute('let other = fixture::pending(false); let timer=time::sleep(5); select { _ = other => (), _ = timer => () };')[0]['failure'] is None
                w.begin(SELECT+' panic!("stop");')
            else:
                assert w.execute(SELECT)[0]['failure'] is None
                w.begin(op=case)
            reply,_=w.settled()
            with w.lock: stderr=bytes(w.streams['stderr'].data)
            # Observe Drop output before ack, not in a following execution.
            assert b'lifecycle closed' in stderr,(case,reply,stderr)
            if case=='destructor':
                assert reply['failure']['category']=='runtime' and reply['state_lost'],reply
                assert stderr.count(b'lifecycle closed')==2,stderr
            elif case in ['interrupt','runtime']:
                assert reply['failure']['category']==('interrupted' if case=='interrupt' else 'runtime') and not reply['state_lost'],reply
            else: assert reply['failure'] is None,reply
            results[case]={'reply':reply,'stderr':stderr.decode()}
            w.handoff()
            if case in ['destructor','shutdown']:
                assert w.p.wait(timeout=3)==(1 if case=='destructor' else 0)
            elif case in ['interrupt','runtime']:
                answer=w.execute('q.await')[0]
                assert answer['text_plain']=='Err("operation cancelled")',answer
                assert w.execute('kept')[0]['text_plain']=='42'
            else:
                assert w.execute('fixture::ready().await?')[0]['text_plain']=='42'
        finally:w.close()
(OUT/'external.json').write_text(json.dumps(results,indent=2)+'\n')
print('external run, eval, session, parked worker, reset, shutdown, interrupt and destructor retirement passed')
