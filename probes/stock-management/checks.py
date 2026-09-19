"""Reproducible final checks; test configurations run serially."""
from pathlib import Path
import subprocess as sp,json,re,hashlib
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';W=H/'target';O=B/'results/stock-management-0067';rows=[]
def run(name,args):
 with (O/(name+'.log')).open('w') as f:p=sp.run(list(map(str,args)),cwd=R,stdout=f,stderr=sp.STDOUT,timeout=1200)
 rows.append({'name':name,'arguments':list(map(str,args)),'status':p.returncode});(O/'checks.json').write_text(json.dumps(rows,indent=2)+'\n');assert p.returncode==0,name
for name,args in [('root-fmt',['cargo','fmt','--all','--','--check']),('tool-fmt',['cargo','fmt','--manifest-path','tools/project/Cargo.toml','--','--check'])]:run(name,args)
for name,features in [('default',[]),('support',['--features','test-support']),('runner',['--no-default-features','--features','count-allocations,project-sources'])]:run('root-'+name,['cargo','test','--locked','--offline',*features,'--','--test-threads=1'])
for name,features in [('default',[]),('support',['--features','test-support'])]:
 run('tool-'+name,['cargo','test','--locked','--offline','--manifest-path','tools/project/Cargo.toml',*features,'--','--test-threads=1'])
 run('clippy-'+name,['cargo','clippy','--locked','--offline','--manifest-path','tools/project/Cargo.toml','--all-targets',*features,'--','-D','warnings'])
run('root-notices',['scripts/third-party-notices.sh','--check']);run('tool-notices',['python3','tools/project/scripts/notices.py','--check'])
for shape,features in [('stock',[]),('runner',['--no-default-features','--features','count-allocations,project-sources'])]:
 text=sp.check_output(['cargo','tree','--locked','--offline','--prefix','none',*features],cwd=R,text=True);(O/(shape+'-tree.txt')).write_text(text)
 assert ('rnx-project v' in text)==(shape=='stock');assert 'polars v' not in text and 'tokio-postgres v' not in text
p=W/'stock-preparation/project';r=json.loads((p/'.rnx/receipt.json').read_text());a=W/'stock-preparation/cache/entries'/r['assembly_key']/'artifacts'/r['executable_blake3'];symbols=sp.check_output(['nm','-C',str(a)],text=True);assert 'rnx_project::' not in symbols
m=(a.parent.parent/'assembly/Cargo.toml').read_text();assert 'default-features = false' in m and 'count-allocations' in m
(O/'feature-checks.json').write_text(json.dumps({'generated_artifact':str(a),'management_symbols':False,'wrapper':m},indent=2)+'\n')
