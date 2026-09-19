from common import *
rows=json.loads((O/"regression.json").read_text()) if "--resume" in sys.argv else []
completed={r["name"] for r in rows if r["status"]==0 or r["name"]=="root-clippy"}
def check(name,args,ok=True):
 if name in completed:return None
 p=run(args,ok=False);(O/(name+'.log')).write_bytes(p.stdout+p.stderr);rows.append({'name':name,'args':list(map(str,args)),'status':p.returncode});save('regression.json',rows);print(name,p.returncode,flush=True)
 if ok:assert p.returncode==0,name
 return p
check('root-fmt',['cargo','fmt','--check']);check('tool-fmt',['cargo','fmt','--manifest-path','tools/project/Cargo.toml','--check'])
for name,flags in [('default',[]),('support',['--features','test-support']),('runner',['--no-default-features','--features','count-allocations,project-sources'])]:check('root-'+name,['cargo','test','--locked','--offline','-j','6',*flags,'--','--test-threads=1'])
for name,flags in [('default',[]),('support',['--features','test-support'])]:
 check('tool-'+name,['cargo','test','--locked','--offline','--manifest-path','tools/project/Cargo.toml','-j','4',*flags,'--','--test-threads=1'])
 check('tool-clippy-'+name,['cargo','clippy','--locked','--offline','--manifest-path','tools/project/Cargo.toml','--all-targets',*flags,'--','-D','warnings'])
check('root-notices',['bash','scripts/third-party-notices.sh','--check']);check('tool-notices',['python3','tools/project/scripts/notices.py','--check']);check('selfcheck',[T/'stock','selfcheck'])
# Root clippy already had findings before this record: preserve rather than hide.
check('root-clippy',['cargo','clippy','--locked','--offline','--all-targets','--','-D','warnings'],ok=False)
for path in ['adapters/postgres','adapters/polars','servers/http-postgres']:
 name=path.replace('/','-');check(name+'-tests',['cargo','test','--locked','--offline','--manifest-path',path+'/Cargo.toml','-j','4','--','--test-threads=1'])
 check(name+'-notices',['python3',path+'/scripts/third-party-notices.py','--check'])
print('regression complete',flush=True)
