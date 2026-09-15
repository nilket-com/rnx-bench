#!/usr/bin/env python3
"""Run record 0038's examples against a supplied release binary (Unix signals)."""
import json, os, pathlib, signal, subprocess, sys, tempfile, time
exe=str(pathlib.Path(sys.argv[1]).resolve())
env={'TZ':'Europe/Paris','TERM':'dumb'}
cases={
 'log': 'time::rfc3339(time::now_ms(), "UTC")?',
 'elapsed': 'let t=time::monotonic_ms(); time::sleep(50).await?; time::monotonic_ms()-t',
 'zones': 'let jan=time::parse("2026-01-15T12:00:00Z")?; let jul=time::parse("2026-07-15T12:00:00Z")?; [time::rfc3339(jan,"America/Chicago")?, time::rfc3339(jan,"Europe/Paris")?, time::rfc3339(jul,"America/Chicago")?, time::rfc3339(jul,"Europe/Paris")?]',
}
results={}
with tempfile.TemporaryDirectory(prefix='rnx-time-example-') as tmp:
 p=pathlib.Path(tmp)/'old';p.write_text('old');os.utime(p,ns=(-1,-1))
 cases['age']='let m=fs::metadata('+json.dumps(str(p))+')?.modified_ms; [m, time::now_ms()-m]'
 for name,source in cases.items():
  r=subprocess.run([exe,'eval',source],env=env,capture_output=True,text=True,check=True)
  results[name]={'source':source,'stdout':r.stdout,'stderr':r.stderr,'exit':r.returncode}
 source='io::eprint("ready\\n"); time::sleep(10000).await?'
 child=subprocess.Popen([exe,'eval',source],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 # Use select so even failure to reach the ready marker cannot hang the probe.
 import select
 if not select.select([child.stderr],[],[],5)[0]:
  child.kill();child.communicate();raise RuntimeError('sleep did not become ready')
 ready=child.stderr.readline();assert ready=='ready\n',ready
 time.sleep(.02);start=time.monotonic();child.send_signal(signal.SIGINT)
 try: stdout,stderr=child.communicate(timeout=.5)
 except subprocess.TimeoutExpired:
  child.kill();child.communicate();raise
 results['cancel']={'source':source,'stdout':stdout,'stderr':ready+stderr,'exit':child.returncode,'seconds_after_signal':time.monotonic()-start}
 assert child.returncode==130 and 'interrupted' in stderr
pathlib.Path('results/time_0038_examples.json').write_text(json.dumps(results,indent=2)+'\n')
