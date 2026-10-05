"""Fresh standalone compilation versus source-to-answer runtimes; no shell/Cargo."""
import hashlib,json,os,pathlib,random,shutil,statistics,subprocess,sys,time
P=pathlib.Path(__file__).resolve().parent
B=P.parents[1]
T=P/'target'
O=pathlib.Path(sys.argv[1]).resolve()
MODE=sys.argv[2] if len(sys.argv)>2 else 'polling'
assert MODE in ('polling','--blocking','--native') and len(sys.argv) in (2,3)
BLOCKING=MODE=='--blocking'
NATIVE=MODE=='--native'
CLOCK=P/'target/clock'
if NATIVE: assert CLOCK.exists(), 'compile the native clock and pass preflight first'
assert not O.exists(), 'choose a new output directory; never overwrite a measured run'
O.mkdir(parents=True)
T.mkdir(exist_ok=True)
AFFINITY=sorted(os.sched_getaffinity(0))
CPU=4 if 4 in AFFINITY else AFFINITY[0]
os.sched_setaffinity(0,{CPU})
RUSTC=pathlib.Path(subprocess.check_output(['rustup','which','rustc'],text=True).strip())
SYSROOT=pathlib.Path(subprocess.check_output([RUSTC,'--print','sysroot'],text=True).strip())
TRIPLE=subprocess.check_output([RUSTC,'-vV'],text=True).split('host: ')[1].splitlines()[0]
ENV=os.environ.copy()
ENV.update(RNX_CONFIG=str(T/'no-config'),RNX_HISTORY=str(T/'history'),TERM='dumb')
LIB=SYSROOT/'lib/rustlib'/TRIPLE/'lib'
ENV['LD_LIBRARY_PATH']=str(LIB)+(':'+ENV['LD_LIBRARY_PATH'] if ENV.get('LD_LIBRARY_PATH') else '')
def save(name,value):
	(O/name).write_text(json.dumps(value,indent=2)+'\n')
def cmd(argv,**kw):
	return subprocess.run(list(map(str,argv)),env=ENV,capture_output=True,timeout=None if BLOCKING else 30,**kw)
def sha(p):
	return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def version(argv):
	r=cmd(argv,text=True)
	return dict(argv=list(map(str,argv)),exit=r.returncode,stdout=r.stdout,stderr=r.stderr)
def compiler(source,flags,output):
	return [str(RUSTC),'--edition=2024','--crate-name','forty_two',*flags,str(P/(source+'.rs')),'-o',str(output)]
CONFIGS={
	'default':[], 'O':['-O'], 'dynamic':['-C','prefer-dynamic'],
	'cgu1':['-C','codegen-units=1'], 'O-dynamic':['-O','-C','prefer-dynamic'],
	'O-cgu1':['-O','-C','codegen-units=1'],
	'dynamic-cgu1':['-C','prefer-dynamic','-C','codegen-units=1'],
	'O-dynamic-cgu1':['-O','-C','prefer-dynamic','-C','codegen-units=1'],
}
CASES={}
WARM={}
for source in ('empty','print','exit'):
	for config,flags in CONFIGS.items():
		name=source+'-'+config
		out=T/('warm-'+name)
		r=cmd(compiler(source,flags,out));assert r.returncode==0 and not r.stdout and not r.stderr,r
		check=cmd([out]);expected=(42,b'') if source=='exit' else (0,b'42\n' if source=='print' else b'')
		assert (check.returncode,check.stdout)==expected and not check.stderr,(name,check)
		WARM[name]=dict(path=str(out),sha256=sha(out),bytes=out.stat().st_size,comment=version(['readelf','-p','.comment',out]))
		CASES['build-'+name]=dict(group='full-build',source=source,config=config,flags=flags,run=False)
for config,flags in CONFIGS.items():
	CASES['answer-print-'+config]=dict(group='compile-and-run',source='print',config=config,flags=flags,run=True)
for source in ('empty','print','exit'):
	for emit in ('metadata','obj'):
		CASES[source+'-'+emit]=dict(group='compile-stage',source=source,flags=['--emit='+emit],run=False)
for config in ('default','O','dynamic'):
	CASES['cached-print-'+config]=dict(group='existing-executable',argv=[WARM['print-'+config]['path']],stdout='42\n')
CASES['true']=dict(group='overhead',argv=['/bin/true'],stdout='')
CASES['rustc-version']=dict(group='overhead',argv=[str(RUSTC),'--version'],stdout=cmd([RUSTC,'--version']).stdout.decode())
RNX=B/'probes/fmt-0167/target/stock'
assert RNX.exists(),'need retained ordinary stock rnx binary from closed 0167'
VERSIONS={'rustc':version([RUSTC,'-vV']),'cc':version(['cc','--version']),'rnx':version([RNX,'version'])}
CASES['rnx-eval']=dict(group='source-to-answer',argv=[str(RNX),'--color=never','eval','42'],stdout='42\n')
CASES['rnx-run']=dict(group='source-to-answer',argv=[str(RNX),'--color=never','run',str(P/'answer.rn')],stdout='42\n')
for name,binary,args,vargs in [
	('python','python3',['-c','print(42)'],['--version']),
	('perl','perl',['-e','print "42\\n"'],['-v']),
	('lua','lua54',['-e','print(42)'],['-v']),
	('luajit','luajit',['-e','print(42)'],['-v']),
	('bun','bun',['-e','console.log(42)'],['--version']),
	('node-official',str(pathlib.Path.home()/'opt/node-v22.22.1-linux-x64/bin/node'),['-e','console.log(42)'],['--version']),
	('ruby','ruby',['-e','puts 42'],['--version']),
	('deno','deno',['eval','console.log(42)'],['--version']),
]:
	path=shutil.which(binary)
	if path:
		CASES[name]=dict(group='source-to-answer',argv=[path,*args],stdout='42\n')
		VERSIONS[name]=version([path,*vargs])
	else:
		VERSIONS[name]={'unavailable':True}
MACHINE={'uname':version(['uname','-a']),'lscpu':version(['lscpu','--json']),'affinity_initial':AFFINITY,'cpu':CPU}
for name,path in {'governor':f'/sys/devices/system/cpu/cpu{CPU}/cpufreq/scaling_governor','driver':f'/sys/devices/system/cpu/cpu{CPU}/cpufreq/scaling_driver','min_khz':f'/sys/devices/system/cpu/cpu{CPU}/cpufreq/scaling_min_freq','max_khz':f'/sys/devices/system/cpu/cpu{CPU}/cpufreq/scaling_max_freq','intel_no_turbo':'/sys/devices/system/cpu/intel_pstate/no_turbo'}.items():
	try:MACHINE[name]=pathlib.Path(path).read_text().strip()
	except OSError:MACHINE[name]=None
save('conditions.json',dict(machine=MACHINE,versions=VERSIONS,rustc_sha256=sha(RUSTC),rnx_sha256=sha(RNX),sources={p.name:sha(p) for p in P.glob('*.rs')},cases=CASES,warm_executables=WARM,rounds=3,samples_per_round=30,warmups=5,driver_sha256=sha(P/'run.py'),native_helper_sha256=sha(CLOCK) if NATIVE else None,native_clock=NATIVE,blocking_wait=BLOCKING,clock='native Instant spawn/capture/blocking-wait; helper launch and serialization excluded' if NATIVE else 'synchronous shell-free spawn/capture/blocking-wait' if BLOCKING else 'synchronous shell-free spawn/capture/timeout-polling-wait',cleanup_before_clock=True,warm_filesystem=True,output_deleted_before_each_sample=True,frame_threshold_ms=[16.7,8.3,6.9],no_Cargo=True,no_LTO=True,no_incremental=True))
ROWS=[]
def sample(name,c):
	if NATIVE:
		if 'argv' in c:
			commands=[c['argv']];expected=[(0,c['stdout'].encode(),b'')]
		else:
			out=T/'sample';out.unlink(missing_ok=True)
			commands=[compiler(c['source'],c['flags'],out)];expected=[(0,b'',b'')]
			if c['run']:commands.append([str(out)]);expected.append((0,b'42\n',b''))
		argv=[str(CLOCK),str(len(commands))]
		for command in commands:argv += [str(len(command)),*command]
		r=cmd(argv);assert r.returncode==0 and not r.stderr,(name,r)
		lines=r.stdout.decode().splitlines();assert len(lines)==1+3*len(commands),(name,lines)
		for i,want in enumerate(expected):
			at=1+3*i;actual=(int(lines[at]),bytes.fromhex(lines[at+1]),bytes.fromhex(lines[at+2]));assert actual==want,(name,actual,want)
		if 'argv' not in c:assert out.exists(),(name,'missing compiler artifact')
		return int(lines[0]),commands
	if 'argv' in c:
		commands=[c['argv']]
		begin=time.perf_counter_ns();r=cmd(c['argv']);ns=time.perf_counter_ns()-begin
		assert (r.returncode,r.stdout,r.stderr)==(0,c['stdout'].encode(),b''),(name,r)
	else:
		out=T/'sample'
		out.unlink(missing_ok=True)
		compile_cmd=compiler(c['source'],c['flags'],out)
		commands=[compile_cmd]
		begin=time.perf_counter_ns();r=cmd(compile_cmd)
		assert (r.returncode,r.stdout,r.stderr)==(0,b'',b''),(name,r)
		if c['run']:
			commands.append([str(out)]);r=cmd([out]);assert (r.returncode,r.stdout,r.stderr)==(0,b'42\n',b''),(name,r)
		ns=time.perf_counter_ns()-begin
		assert out.exists(),(name,'missing compiler artifact')
	return ns,commands
for name,c in CASES.items():
	for _ in range(5):sample(name,c)
for repeat in range(3):
	jobs=[(name,i) for name in CASES for i in range(30)]
	random.Random(42000+repeat).shuffle(jobs)
	for name,i in jobs:
		ns,commands=sample(name,CASES[name]);row=dict(case=name,group=CASES[name]['group'],repeat=repeat,sample=i,ns=ns,commands=commands)
		ROWS.append(row)
		with (O/'samples.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
	print('round',repeat,'complete',flush=True)
# The fastest full-build case is selected descriptively, not a held-out contest.
fastest=min((n for n,c in CASES.items() if c['group']=='full-build'),key=lambda n:statistics.median(r['ns'] for r in ROWS if r['case']==n))
selected=CASES[fastest]
for label,affinity in [('human-unpinned',AFFINITY),('four-cores',AFFINITY[:4])]:
	os.sched_setaffinity(0,set(affinity))
	for _ in range(5):sample(fastest,selected)
	for i in range(90):
		ns,commands=sample(fastest,selected);row=dict(case=label,selected=fastest,group='affinity-control',repeat=i//30,sample=i%30,ns=ns,commands=commands,affinity=affinity)
		ROWS.append(row)
		with (O/'samples.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
os.sched_setaffinity(0,{CPU})
save('selected-affinity-control.json',{'case':fastest,'rule':'lowest median of the pinned full-build configurations','four_core_policy':'first four allowed CPUs (0,1,2,3 here)'})
# Untimed attribution: stable exec chain/thread creations and installed nightly.
trace=O/'exec-and-clones.txt'
r=cmd(['strace','-f','-e','trace=execve,clone,clone3','-o',str(trace),*compiler(selected['source'],selected['flags'],T/'trace')])
assert r.returncode==0,r.stderr
nightly=subprocess.run(['rustup','which','--toolchain','nightly','rustc'],capture_output=True,text=True)
if nightly.returncode==0:
	n=nightly.stdout.strip();save('nightly-version.json',version([n,'-vV']))
	r=cmd([n,*compiler(selected['source'],selected['flags'],T/'nightly')[1:],'-Z','time-passes'])
	(O/'nightly-time-passes.txt').write_bytes(r.stderr)
	save('nightly-status.json',dict(exit=r.returncode,stdout=r.stdout.decode(),configuration=fastest,note='different installed compiler; attribution only, not a stable timing decomposition'))
else:save('nightly-status.json',{'unavailable':True})
print('timings and attribution complete',flush=True)
