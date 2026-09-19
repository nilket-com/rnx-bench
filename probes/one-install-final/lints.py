from common import *
import re,collections
p=run(['cargo','clippy','--locked','--offline','--all-targets','-j','4','--','-D','warnings'],cwd=T/'before',ok=False);(O/'baseline-clippy.log').write_bytes(p.stdout+p.stderr)
def diagnostics(text):return collections.Counter(re.findall(r'^error: (?!could not compile)(.+)$',text,re.M))
a=diagnostics((O/'baseline-clippy.log').read_text());b=diagnostics((O/'root-clippy.log').read_text());save('clippy-comparison.json',{'baseline':dict(a),'current':dict(b),'added':dict(b-a),'removed':dict(a-b),'baseline_status':p.returncode});print('clippy added',dict(b-a),flush=True)
assert not b-a
