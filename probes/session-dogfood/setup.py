"""Freeze ordinary product binaries; keep projects, cache and user state private."""
from pathlib import Path
import json, os, shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target'
(W/'bin').mkdir(parents=True,exist_ok=True)
for src,name in [(R/'target/debug/rnx','rnx'),(R/'tools/project/target/debug/rnx-project','rnx-project')]:
 shutil.copy2(src,W/'bin'/name)
env={k:v for k,v in os.environ.items() if not k.startswith(('RNX_','CARGO_','RUST','POLARS_'))}
env.update(TERM='xterm-256color',POLARS_MAX_THREADS='1',PYTHONDONTWRITEBYTECODE='1',RNX_DEP_RUNTIME=str(R),RNX_PROJECT_TOOL=str(W/'bin/rnx-project'),RNX_PROJECT_CACHE=str(W/'cache'),RNX_CONFIG=str(W/'absent-config'),XDG_STATE_HOME=str(W/"state with ' quote"))
(W/'env.json').write_text(json.dumps(env,indent=2)+'\n')
print('ordinary binaries frozen',flush=True)
