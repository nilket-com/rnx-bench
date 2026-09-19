from common import *
source=(B/'probes/stock-management/checks.py').read_text()
source=source.replace("H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/stock-management-0067';rows=[]", "from common import *\nW=T\nrows=[]")
source=source[:source.index("p=W/'stock-preparation/project'")]
(O/'checks-effective.py').write_text(source)
exec(compile(source,'checks-effective.py','exec'))
