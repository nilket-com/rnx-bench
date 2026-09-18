"""Disjoint installer intervals in an archived isolated tool; ordinary control."""
from pathlib import Path
import os,json,subprocess as sp,time,hashlib,shutil,random,statistics,re
H=Path(__file__).resolve().parent;B=H.parents[1];W=H/'target';O=B/'results/runtime-cost-0064';state=json.loads((W/'setup.json').read_text());C=Path(state['checkout']);T=Path(state['tool']);E=state['env']
P=W/'timed-tool';assert not P.exists();shutil.copytree(C/'tools/project',P,ignore=shutil.ignore_patterns('target'))
p=P/'src/runtime_install/hooks.rs';s=p.read_text();needle='pub(super) fn point(name: &str) -> Result<(), String> {';s=s.replace(needle,needle+'''
    if matches!(name, "cost-start" | "after-snapshot" | "after-copy" | "after-index" | "before-entry-rename" | "after-entry-sync" | "before-current-write" | "after-current-sync" | "cost-end") {
        static START: std::sync::OnceLock<std::time::Instant> = std::sync::OnceLock::new();
        let start = START.get_or_init(std::time::Instant::now);
        eprintln!("RNX_COST {} {}", name, start.elapsed().as_nanos());
    }
''');p.write_text(s)
p=P/'src/runtime_install/unix.rs';s=p.read_text().replace('fn install(source: &Path) -> Result<Installation, String> {','fn install(source: &Path) -> Result<Installation, String> {\n hooks::point("cost-start")?;').replace('\n\tresult.map_err(|e| {','\n hooks::point("cost-end")?;\n\tresult.map_err(|e| {');p.write_text(s)
# Save exact source files: instrumentation only; snapshot source never modified.
for name in ['hooks.rs','unix.rs']:(O/('timed-'+name)).write_bytes((P/'src/runtime_install'/name).read_bytes())
log=sp.run(['cargo','build','--release','--locked','--offline','--manifest-path',str(P/'Cargo.toml'),'--target-dir',str(W/'timed-tool-build')],env=E,capture_output=True,text=True);(O/'timed-tool-build.log').write_text(log.stdout+log.stderr);assert log.returncode==0
while len(json.loads((W/'setup.json').read_text())['cells']) != 4: time.sleep(1)
I=W/'timed-tool-build/release/rnx-project';cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu});rows=[];rng=random.Random(6405)
for repeat in range(2):
 jobs=[(kind,n) for kind in ['ordinary','timed'] for n in range(10)];rng.shuffle(jobs)
 for kind,n in jobs:
  data=W/f'install-{repeat}-{kind}-{n}';env=dict(E,XDG_DATA_HOME=str(data));start=time.perf_counter_ns();p=sp.run([str(T if kind=='ordinary' else I),'runtime','install','--from',str(C)],env=env,capture_output=True,text=True,timeout=60);ms=(time.perf_counter_ns()-start)/1e6;assert p.returncode==0,(p.stdout,p.stderr)
  id=p.stdout.split('runtime ',1)[1].splitlines()[0];assert id==state['installation']['id'];phases={name:int(ns)/1e6 for name,ns in re.findall(r'RNX_COST ([\w-]+) (\d+)',p.stderr)}
  if kind=='timed':assert len(phases)==9,phases
  rows.append(dict(repeat=repeat,kind=kind,index=n,wall_ms=ms,phases_ms=phases));(O/'installation-samples.json').write_text(json.dumps(rows,indent=2)+'\n')
# Count all retained files by both logical bytes and filesystem blocks.
root=Path(state['installed']);def_count=lambda paths:dict(files=len(paths),logical_bytes=sum(p.stat().st_size for p in paths),allocated_bytes=sum(p.stat().st_blocks*512 for p in paths))
source=[p for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts];git=[p for p in (root/'.git').rglob('*') if p.is_file()];allfiles=[p for p in root.parent.rglob('*') if p.is_file()]
result=dict(cpu=cpu,source=def_count(source),git=def_count(git),entry=def_count(allfiles),timed_tool_sha256=hashlib.sha256(I.read_bytes()).hexdigest(),ordinary_tool_sha256=hashlib.sha256(T.read_bytes()).hexdigest())
result['medians']={f'{repeat}-{kind}':statistics.median(r['wall_ms'] for r in rows if r['repeat']==repeat and r['kind']==kind) for repeat in range(2) for kind in ['ordinary','timed']}
intervals=[('initial validation','cost-start','after-snapshot'),('copy and file sync','after-snapshot','after-copy'),('independent index','after-copy','after-index'),('validation metadata and tree sync','after-index','before-entry-rename'),('entry publication','before-entry-rename','after-entry-sync'),('final validation','after-entry-sync','before-current-write'),('selection publication','before-current-write','after-current-sync')]
result['phase_medians_ms']={name:statistics.median(r['phases_ms'][end]-r['phases_ms'][start] for r in rows if r['kind']=='timed') for name,start,end in intervals}
(O/'installation-summary.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS 40 installation samples',result['medians'],flush=True)
