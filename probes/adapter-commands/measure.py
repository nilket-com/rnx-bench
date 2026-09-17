"""Two interleaved repeats, both consumers, all three launch routes and modes."""
from common import *
import importlib.util, random, statistics, tempfile

spec = importlib.util.spec_from_file_location('terminal_fixture', B / 'probes/project-interactive/common.py')
terminal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terminal)
cpu = min(os.sched_getaffinity(0))
os.sched_setaffinity(0, {cpu})
a = artifact()
assert artifact(APPS[1]) == a
preview = 'DataFrame: 2 rows × 2 columns\n"category": string | "total": i64\n"a" | 2\n"🦀" | 7\n\n'
commands = {}
for i, app in enumerate(APPS):
    commands[app.name] = {}
    for mode in ['pipeline','eval','session']:
        commands[app.name][mode] = {}
        for kind in ['default','verify','direct']:
            flags = ['--verify'] if kind == 'verify' else []
            if mode == 'pipeline':
                cmd = [str(a),'run',str(app / 'main.rn')] if kind == 'direct' else command('run',app,[*flags,'--'])
            elif mode == 'eval':
                expr = 'polars::lit(1).is_ok()'
                cmd = [str(a),'--color=never','eval',expr] if kind == 'direct' else command('eval',app,[*flags,'--color=never','--',expr])
            else:
                cmd = [str(a),'--no-splash','--color=never','repl'] if kind == 'direct' else command('session',app,[*flags,'--no-splash','--color=never'])
            commands[app.name][mode][kind] = cmd

def sample(index, mode, kind):
    app = APPS[index]
    cmd = commands[app.name][mode][kind]
    with tempfile.TemporaryDirectory(prefix='rnx-cache-polars-measure-') as d:
        cwd = Path(d)
        env = dict(ENV,RNX_CONFIG=str(cwd / 'absent'),RNX_HISTORY=str(cwd / 'history'))
        if mode == 'session':
            start = time.perf_counter_ns()
            t = terminal.Terminal(cmd,cwd,env)
            try:
                out = t.read()
                ms = (time.perf_counter_ns()-start)/1e6
                assert out == '\r[1] > \r', repr(out)
                os.write(t.master,b':q\n')
                t.read(False)
                assert t.p.wait(timeout=5) == 0
            finally:
                t.close()
        else:
            argv = cmd + [str(cwd)] if mode == 'pipeline' else cmd
            start = time.perf_counter_ns()
            p = subprocess.run(argv,cwd=cwd,env=env,capture_output=True,text=True,timeout=30)
            ms = (time.perf_counter_ns()-start)/1e6
            expected = f'consumer-{index+1}\n' + preview if mode == 'pipeline' else 'true\n'
            assert p.returncode == 0 and p.stdout == expected and not p.stderr,(argv,p.returncode,p.stdout,p.stderr)
            if mode == 'pipeline':
                assert (cwd / 'tiny.csv').is_file() and (cwd / 'tiny.parquet').is_file()
        return ms

for index in range(2):
    for mode in ['pipeline','eval','session']:
        for kind in ['default','verify','direct']:
            sample(index,mode,kind)
rows = []
(O / 'journal.jsonl').write_text('')
for repeat in range(2):
    for n in range(20):
        jobs = [(i,m,k) for i in range(2) for m in ['pipeline','eval','session'] for k in ['default','verify','direct']]
        random.Random(61500 + repeat*100 + n).shuffle(jobs)
        for i, mode, kind in jobs:
            row = {'repeat':repeat,'sample':n,'project':APPS[i].name,'mode':mode,'kind':kind,'ms':sample(i,mode,kind)}
            rows.append(row)
            with (O / 'journal.jsonl').open('a') as f:
                f.write(json.dumps(row)+'\n')
    print('repeat',repeat,'complete',flush=True)
summary = {app.name:{m:{k:[statistics.median(x['ms'] for x in rows if x['project']==app.name and x['mode']==m and x['kind']==k and x['repeat']==r) for r in range(2)] for k in ['default','verify','direct']} for m in ['pipeline','eval','session']} for app in APPS}
save('samples.json',rows)
save('summary.json',summary)
save('timing-conditions.json',{'cpu':cpu,'polars_threads':1,'repeats':2,'samples_per_cell_per_repeat':20,'samples':len(rows),'seed':61500,
    'commands':commands,'terminal':'xterm-256color 120x30',
    'clock':'perf_counter_ns; no-shell spawn/capture/wait for eval and pipeline; PTY allocation/spawn through first prompt for session; quit/reap outside clock',
    'cache':'warm after one unmeasured launch per cell; no receipt rewriting; derived maps established before measurement',
    'outputs':'every pipeline checks exact stdout (including Parquet readback and repeated collect) and two created files; every eval true; every session exact first prompt and zero exit',
    'tool_sha256':sha(T),'artifact_sha256':sha(a),
    'rnx_head':subprocess.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip()})
print(json.dumps(summary,indent=2),flush=True)
for project,modes in summary.items():
    for mode,values in modes.items():
        for r in range(2):
            assert values['default'][r]-values['direct'][r] <= 25,(project,mode,r,'25 ms overhead gate failed')
