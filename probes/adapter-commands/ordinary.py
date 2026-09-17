"""Product build: authoring fault/pause hooks compile out."""
from common import *
import tempfile
with tempfile.TemporaryDirectory(prefix='rnx-add-ordinary-') as d:
 w=Path(d);n=w/'runtime';a=w/'app';a.mkdir();(n/'adapters/polars').mkdir(parents=True)
 (n/'Cargo.toml').write_text('[package]\nname="rnx"\n')
 (n/'adapters/polars/Cargo.toml').write_text('[package]\nname="rnx-polars"\n[dependencies]\nrnx={path="../.."}\n')
 (a/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[runtime]\npath="../runtime"\n')
 marker=w/'must-not-appear'
 env=dict(ENV,RNX_PROJECT_FAIL='before-add-rename',RNX_PROJECT_PAUSE='after-add-temp',RNX_PROJECT_PAUSE_FILE=str(marker))
 p=subprocess.run(command('add',a,['polars']),env=env,capture_output=True,text=True,timeout=5)
 assert p.returncode==0 and 'added polars' in p.stdout and not marker.exists(),p
 (O/'ordinary-add.log').write_text(p.stdout+p.stderr)
print('PASS ordinary authoring: fault and pause hooks absent',flush=True)
