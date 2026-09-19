from common import *
assert not (T/'before').exists()
assert not run(['git','-c','color.ui=false','diff','1b894e0','--','.',':(exclude)README.md',':(exclude)tools/project/README.md',':(exclude)plans/**']).stdout
save('source.json',{'baseline':'94f5f3f','product':'1b894e0','working_head':run(['git','rev-parse','HEAD']).stdout.decode().strip(),'allowed_differences':'READMEs and plan/evidence text only'})
run(['git','worktree','add','--detach',T/'before','94f5f3f'])
for name,source in [('before',T/'before'),('after',R)]:
 p=run(['cargo','build','--release','--locked','--offline','--bin','rnx','-j','8'],cwd=source);(O/(name+'-build.log')).write_bytes(p.stdout+p.stderr)
 shutil.copy2(source/'target/release/rnx',T/name.replace('before','baseline').replace('after','stock'))
save('binaries.json',{k:{'path':str(T/p),'sha256':sha(T/p),'size':(T/p).stat().st_size} for k,p in [('before','baseline'),('after','stock')]})
print('matched binaries ready',flush=True)
