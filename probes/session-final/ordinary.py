"""Freeze ordinary release binaries, then rerun real cold/cache journeys."""
from pathlib import Path
import subprocess,os,shutil,json
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target/dogfood';O=B/'results/session-final-0063/dogfood';O.mkdir(parents=True,exist_ok=True)
(W/'bin').mkdir(parents=True,exist_ok=True)
for src,name in [(R/'target/release/rnx','rnx'),(R/'tools/project/target/release/rnx-project','rnx-project')]:shutil.copy2(src,W/'bin'/name)
env={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','CARGO_','RUST','POLARS_'))}
env.update(TERM='xterm-256color',POLARS_MAX_THREADS='1',PYTHONDONTWRITEBYTECODE='1',RNX_DEP_RUNTIME=str(R),RNX_PROJECT_TOOL=str(W/'bin/rnx-project'),RNX_PROJECT_CACHE=str(W/'cache'),RNX_CONFIG=str(W/'absent-config'),XDG_STATE_HOME=str(W/"state with ' quote"))
(W/'env.json').write_text(json.dumps(env,indent=2)+'\n')
p=subprocess.run(['python3','probes/session-dogfood/check.py'],cwd=B,env=dict(os.environ,RNX_DOGFOOD_TARGET=str(W),RNX_DOGFOOD_RESULTS=str(O)))
raise SystemExit(p.returncode)
