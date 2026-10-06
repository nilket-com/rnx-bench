import hashlib,json,pathlib,subprocess,time
repo=pathlib.Path('/home/me/work/.worktrees/rune-0176')
out=pathlib.Path('/home/me/work/.worktrees/rnx-bench-0176/results/outlined-range-0176/source-tests/final')
out.mkdir(parents=True,exist_ok=False)
env={'PATH':'/home/me/.cargo/bin:/usr/bin:/bin','HOME':'/home/me','LANG':'C.UTF-8','CARGO_HOME':'/home/me/.cargo','RUSTUP_HOME':'/home/me/.rustup','CARGO_INCREMENTAL':'0'}
rev=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
assert rev.startswith('6f54bd32')
assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)
jobs=[('all-features',['cargo','test','--locked','--offline','-p','rune','--all-targets','--all-features']),('non-tracing',['cargo','test','--locked','--offline','-p','rune','--lib','--no-default-features','--features','alloc,bench,byte-code,capture-io,cli,disable-io,doc,emit,fmt,languageserver,musli,serde,std,workspace','range_iteration']),('no-std',['cargo','check','--locked','--offline','-p','rune','--no-default-features','--features','alloc'])]
for name,argv in jobs:
 start=time.time()
 with (out/(name+'.log')).open('wb') as f:
  r=subprocess.run(argv,cwd=repo,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
 record={'name':name,'argv':argv,'cwd':str(repo),'env':env,'source':rev,'status':r.returncode,'start':start,'end':time.time(),'lock':'/tmp/rnx-runtime-bench.lock'}
 (out/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n')
 assert r.returncode==0,(name,r.returncode)
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==rev
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)
print('FINAL TEST CHAIN PASS',rev,flush=True)
