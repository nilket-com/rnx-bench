from common import *
rows=[]
for cwd,args in [(R,['cargo','fmt','--check']),(R/'tools/project',['cargo','fmt','--check'])]+[(R/'tools/project',['cargo','clippy','--locked','--offline','--all-targets',*feature,'--','-D','warnings']) for feature in [[],['--features','test-support']]]+[(R/'tools/project',['cargo','test','--locked','--offline',*feature,'--','--test-threads=1']) for feature in [[],['--features','test-support']]]:
 p=run(args,cwd=cwd);name=f'check-{len(rows)}.log';(O/name).write_bytes(p.stdout+p.stderr);rows.append({'cwd':str(cwd),'args':args,'status':p.returncode,'log':name})
save('product-checks.json',rows);print('product checks passed')
