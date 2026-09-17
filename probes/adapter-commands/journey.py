"""Both consumers keep native frames across inputs, errors and reset."""
from common import *
import importlib.util, tempfile

spec = importlib.util.spec_from_file_location('terminal_fixture', B / 'probes/project-interactive/common.py')
terminal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terminal)
results = {}
for app in APPS:
    with tempfile.TemporaryDirectory(prefix='rnx-cache-polars-journey-') as d:
        cwd = Path(d)
        env = dict(ENV,RNX_CONFIG=str(cwd/'absent'),RNX_HISTORY=str(cwd/'history'))
        for expr in ['polars::lit(1).is_ok()', 'polars::read_csv("absent.csv", [("v","i64")])']:
            p = subprocess.run(command('eval',app,['--color=never','--',expr]),env=env,cwd=cwd,capture_output=True,text=True,timeout=30)
            direct = subprocess.run([artifact(app),'--color=never','eval',expr],env=env,cwd=cwd,capture_output=True,text=True,timeout=30)
            assert (p.returncode,p.stdout,p.stderr)==(direct.returncode,direct.stdout,direct.stderr)
        t = terminal.Terminal(command('session',app,['--no-splash','--color=never']),cwd,env)
        try:
            t.read()
            t.send('fs::write_new("tiny.csv", "category,value\\na,1\\na,2\\n🦀,3\\n🦀,4\\nmissing,\\n").unwrap();')
            t.send('let frame = polars::read_csv("tiny.csv", [("category","string"),("value","i64")]).unwrap();')
            t.send('let grouped = frame.lazy().filter(polars::col("value").gt(polars::lit(1).unwrap())).group_by([polars::col("category")]).unwrap();')
            t.send('let plan = grouped.agg([polars::col("value").sum().alias("total")]).unwrap().sort(["category"]).unwrap();')
            t.send('let result = plan.collect().unwrap();')
            out = t.send('println!("{}", result.preview().unwrap());')
            assert '"a" | 2' in out and '"🦀" | 7' in out,out
            out = t.send('frame.lazy().sort(["missing"]).unwrap().collect()')
            assert 'Err' in out and 'missing' in out,out
            out = t.send('println!("{}", frame.preview().unwrap());')
            assert '5 rows' in out,out
            t.send('result.write_parquet_new("tiny.parquet").unwrap();')
            out = t.send('assert!(polars::read_parquet("tiny.parquet").unwrap().preview().unwrap() == result.preview().unwrap());')
            assert 'error' not in out.lower(),out
            # The original reusable lazy plan is still live after the error.
            out = t.send('assert!(plan.collect().unwrap().preview().unwrap() == result.preview().unwrap());')
            assert 'error' not in out.lower(),out
            t.send(':reset')
            out = t.send('frame')
            assert 'No local variable' in out,out
            out = t.send('polars::lit(1).is_ok()')
            assert 'true' in out,out
            os.write(t.master,b':q\n')
            t.read(False)
            assert t.p.wait(timeout=5)==0
        finally:
            (O / (app.name+'-pty.bin')).write_bytes(t.log)
            (O / (app.name+'-pty.txt')).write_text('\n'.join(line.rstrip() for line in terminal.text(t.log).splitlines())+'\n')
            t.close()
        results[app.name] = {'eval_matches_direct':True,'frame_survives_error':True,'parquet_roundtrip':True,'repeated_collect':True,'reset_drops_binding_keeps_extension':True}
save('journey.json',results)
print('PASS both shared Polars consumers: eval and live session recovery',flush=True)
