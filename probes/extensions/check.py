#!/usr/bin/env python3
"""External assembly checks; saves complete replies and subprocess output."""
import os, pathlib, subprocess, json, tempfile, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
RNX = ROOT.parent/'rnx'
OUT = ROOT/'results/extensions-0051'
APP = pathlib.Path(sys.argv[1]).resolve()
BROKEN = APP.with_name('broken')
sys.path.insert(0, str(RNX/'tests'))
from worker_parent import Parent
results = {}
with tempfile.TemporaryDirectory(prefix='rnx extensions ') as tmp:
    tmp = pathlib.Path(tmp)
    env = dict(os.environ, TERM='xterm', RNX_CONFIG=str(tmp/'absent'), RNX_HISTORY=str(tmp/'history'), NO_COLOR='1')
    env.pop('RNX_FIXTURE_MARKER', None)
    env.pop('RNX_MEMORY_CEILING', None)
    def run(name, args, source=None, more=None, binary=APP):
        r = subprocess.run([str(binary), *args], input=source, env={**env, **(more or {})}, text=True, capture_output=True, timeout=30)
        results[name] = dict(exit=r.returncode, stdout=r.stdout, stderr=r.stderr)
        return r
    def ok(name, args, expected, **kw):
        r = run(name, args, **kw)
        assert r.returncode==0 and r.stdout==expected, (name,r)
    r=run('stock refuses extension', ['eval','fixture::answer()'], binary=RNX/'target/release/rnx')
    assert r.returncode==1 and 'missing item' in r.stderr.lower(),r
    ok('eval', ['eval','fixture::answer()'], '42\n')
    ok('await', ['eval','fixture::later(20).await?'], '20\n')
    file = tmp/'main.rn'
    file.write_text('pub fn main(_) { fixture::answer() }')
    ok('run', ['run',str(file)], '42\n')
    file.write_text('pub fn main(_) { fixture::fail()?; Ok(()) }')
    r=run('file error', ['run',str(file)]);assert r.returncode==1 and r.stderr=='error: fixture failure\n',r
    r=run('eval returned error', ['eval','fixture::fail()']);assert r.returncode==1 and r.stderr=='error: fixture failure\n',r
    # Preserve the known top-level ? wrapper limitation, not a new contract.
    r=run('eval question-mark observation', ['eval','fixture::fail()?']);assert r.returncode==1 and 'Expected type' in r.stderr
    for case,name in [('', 'sibling'), ('json','json'), ('std','std'), ('duplicate','fixture'), ('help','sibling'), ('install','sibling'), ('panic','sibling'), ('empty',''), ('invalid','two words')]:
        r=run('refusal '+case,['--no-splash'],more={'RNX_FIXTURE_CASE':case},binary=BROKEN,source='42\n:q\n')
        assert r.returncode==1 and not r.stdout and r.stderr.startswith(f'error: extension `{name}` could not be installed:'),r
        assert len(r.stderr.splitlines())==1,r
        assert 'thread ' not in r.stderr,r
    r=run('other thread panic',['eval','fixture::answer()'],more={'RNX_FIXTURE_CASE':'thread-panic'},binary=BROKEN)
    assert r.returncode==0 and 'other thread boom' in r.stderr and r.stdout=='42\n',r
    ok('module replacement', ['eval','fs::extension_probe()'], '17\n', more={'RNX_FIXTURE_CASE':'replace'},binary=BROKEN)
    marker=tmp/'marker'
    for command in ['version','--help','selfcheck']:
        r=run('no hook '+command,[command],more={'RNX_FIXTURE_MARKER':str(marker)})
        assert r.returncode==0 and not marker.exists(),r
    r=run('one hook',['eval','1'],more={'RNX_FIXTURE_MARKER':str(marker)})
    assert r.returncode==0 and marker.read_text()=='builder\n';marker.unlink()
    config=tmp/'config.rn';config.write_text('pub fn main() { fixture::answer() }')
    r=run('settings ordering',['--no-splash'],source='fixture::answer()\n:help fixture::answer\n:reset\nfixture::answer()\n:q\n',more={'RNX_CONFIG':str(config),'RNX_FIXTURE_MARKER':str(marker)})
    assert r.returncode==0 and marker.read_text()=='builder\n',r
    assert r.stderr.index('config') < r.stderr.index('fixture builder marker'),r
    assert r.stdout.count('42')>=2 and 'answer() -> 42' in r.stdout,r
    w=Parent(str(APP),env)
    try:
        a=w.execute('fixture::answer()')[0];assert a['text_plain']=='42',a
        w.execute('let saved = 7;')
        w.begin(op='reset');settled,_=w.settled();w.handoff()
        b=w.execute('fixture::answer()')[0];assert b['text_plain']=='42',b
        c=w.execute('saved')[0];assert c['failure'] is not None,c
        results['worker']={'ready':w.ready,'before':a,'reset':settled,'after':b,'fresh':c}
    finally:w.close()
    # A genuine valid inherited transport; installation failure must precede ready.
    read_child, write_parent=os.pipe();read_parent, write_child=os.pipe()
    try:
        p=subprocess.Popen([str(BROKEN),'worker','--control-read',str(read_child),'--control-write',str(write_child)],pass_fds=(read_child,write_child),env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        os.close(read_child);os.close(write_child)
        stdout,stderr=p.communicate(timeout=10)
        control=os.read(read_parent,4096)
        results['worker startup refusal']=dict(exit=p.returncode,stdout=stdout.decode(),stderr=stderr.decode(),control=control.decode())
        assert p.returncode==1 and not control and not stdout and b'extension `sibling`' in stderr,results['worker startup refusal']
    finally:os.close(write_parent);os.close(read_parent)
(OUT/'assembly.json').write_text(json.dumps(results,indent=2)+'\n')
print('assembly, failure, ordering, reset and worker gates passed')
