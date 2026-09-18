from pathlib import Path
import subprocess as sp,json
b=Path(__file__).resolve().parents[2];r=b.parent/'rnx';o=b/'results/nested-product-0065';rows=[]
commands=[('fmt',['cargo','fmt','--manifest-path','tools/project/Cargo.toml','--check'])]
for feature in [[],['--features','test-support']]:
 name='support' if feature else 'default'
 commands += [(f'clippy-{name}',['cargo','clippy','--locked','--offline','--manifest-path','tools/project/Cargo.toml','--all-targets',*feature,'--','-D','warnings']), (f'tests-{name}',['cargo','test','--locked','--offline','--manifest-path','tools/project/Cargo.toml',*feature,'--','--test-threads=1'])]
commands += [('notices',['python3','tools/project/scripts/notices.py','--check'])]
for name,args in commands:
 with (o/(name+'.log')).open('w') as f:p=sp.run(args,cwd=r,stdout=f,stderr=sp.STDOUT)
 rows.append(dict(name=name,args=args,status=p.returncode));(o/'checks.json').write_text(json.dumps(dict(complete=False,checks=rows),indent=2)+'\n');assert p.returncode==0,name
 print('PASS',name,flush=True)
(o/'checks.json').write_text(json.dumps(dict(complete=True,checks=rows),indent=2)+'\n')
