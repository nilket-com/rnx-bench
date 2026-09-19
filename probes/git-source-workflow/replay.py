from common import *
import shutil,sys
(O/'scripts').mkdir(exist_ok=True)
assert (T/'b3').is_file()
s=(B/'probes/stock-management/replay.py').read_text()
s=s.replace("H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/stock-management-0067';W=H/'target'",'from common import *\nW=T')
s=s.replace("results/stock-management-0067/", "results/git-source-workflow-0067/")
(O/'replay-effective.py').write_text(s)
exec(compile(s,'replay-effective.py','exec'))
