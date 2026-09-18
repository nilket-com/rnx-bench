#!/usr/bin/env python3
import collections,hashlib,json,os,pathlib,random,statistics,struct,subprocess,time
HERE=pathlib.Path(__file__).resolve().parent
BENCH=HERE.parents[1]
R=BENCH/'results/hash-choice-0065'
BIN=HERE/'target/release/rnx-hash-choice-probe'
CONFIG=HERE/'target/inputs.json'
inputs=json.loads(CONFIG.read_text()); root=pathlib.Path(inputs['root'])
# External reference construction: Python hashes and frames independently.
ref=json.loads(subprocess.check_output([str(BIN),'reference',str(CONFIG)]))
(R/'blake-reference.json').write_text(json.dumps(ref,indent=2)+'\n')
b3=dict(ref['files']); rows=[]
old=hashlib.sha256(b'rnx-tree-v1\0'); new=hashlib.sha256(b'rnx-tree-probe-digests-v2\0')
# Blake framing hashed independently by reference command added below via file input.
bframe=bytearray(b'rnx-tree-probe-digests-v2\0')
for p in sorted(inputs['paths']):
    f=root/p; b=f.read_bytes(); name=p.encode(); executable=bool(f.stat().st_mode&0o111)
    prefix=struct.pack('>Q',len(name))+name+bytes([executable])+struct.pack('>Q',len(b))
    d=hashlib.sha256(b).hexdigest()
    old.update(prefix+b); new.update(prefix+bytes.fromhex(d)); bframe+=prefix+bytes.fromhex(b3[p])
    rows.append({'path':p,'bytes':len(b),'executable':executable,'sha256':d})
frame=HERE/'target/blake-frame';frame.write_bytes(bframe)
btree=subprocess.check_output([str(BIN),'hash-reference',str(frame)],text=True).strip()
artifact=pathlib.Path(inputs['artifact']); ab=artifact.read_bytes()
artifact_sha=hashlib.sha256(ab).hexdigest(); del ab
prov=json.loads((R/'provenance.json').read_text())
assert old.hexdigest()==prov['runtime_sha256_v1']
assert artifact_sha==prov['artifact_sha256']
expected={}
for alg,d in [('double-sha256',old.hexdigest()),('single-sha256',new.hexdigest()),('blake3',btree)]:
    fs=[dict(f,sha256=b3[f['path']]) if alg=='blake3' else f for f in rows]
    expected[alg]={'root':str(root),'files':fs,'sha256':d}
(R/'expected.json').write_text(json.dumps({'trees':expected,'artifact_sha256':artifact_sha,'artifact_blake3':ref['artifact']},indent=2)+'\n')
# Distinct physical performance cores, as reported by lscpu on this host.
allowed=os.sched_getaffinity(0)
cpulines=subprocess.check_output(['lscpu','-p=CPU,CORE,SOCKET,ONLINE'],text=True)
seen=set(); cores=[]
for line in cpulines.splitlines():
    if line.startswith('#'):continue
    cpu,core,sock,on=line.split(',');cpu=int(cpu)
    if cpu in allowed and on=='Y' and (core,sock) not in seen:
        seen.add((core,sock));cores.append(cpu)
assert len(cores)>=4
one=[cores[0]];four=cores[:4]
cells=[(w,a) for w in ['tree','native'] for a in ['double-sha256','single-sha256','blake3']]
cells += [('artifact',a) for a in ['single-sha256','blake3','sha256-1m','blake3-1m','parallel-16k','parallel-1m']]
def sample(cell):
    workload,alg=cell
    cpus=four if alg.startswith('parallel') else one
    os.sched_setaffinity(0,cpus)
    begin=time.perf_counter_ns()
    p=subprocess.run([str(BIN),workload,alg,str(CONFIG)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    wall=(time.perf_counter_ns()-begin)/1e6
    assert not p.stderr,p.stderr
    output=json.loads(p.stdout); actual=output['result']
    if workload=='artifact':
        want={'path':artifact.name,'bytes':artifact.stat().st_size,'executable':bool(artifact.stat().st_mode&0o111),'sha256':artifact_sha if alg in ('single-sha256','sha256-1m') else ref['artifact']}
    else:want=expected[alg]
    assert actual==want,(cell,actual.get('sha256'),want.get('sha256'))
    return {'workload':workload,'algorithm':alg,'cpus':cpus,'inside_ms':output['ms'],'wall_ms':wall,'digest':actual['sha256'],'validated':True}
assert not (R/'samples.jsonl').exists(),'save/remove previous journal before measuring'
for c in cells:
    for _ in range(2):sample(c)
with (R/'samples.jsonl').open('x') as out:
    for repeat in range(2):
        schedule=cells*30;random.Random(650101+repeat).shuffle(schedule)
        for i,c in enumerate(schedule):
            s=sample(c);s.update(repeat=repeat,position=i);out.write(json.dumps(s)+'\n');out.flush()
        print('repeat complete',repeat,flush=True)
os.sched_setaffinity(0,allowed)
measure={'samples':720,'cells':12,'samples_per_cell':30,'repeats':2,'seed_base':650101,'warmups_per_cell':2,'single_cpu':one,'parallel_cpus':four,'binary_sha256':hashlib.sha256(BIN.read_bytes()).hexdigest(),'rustc':subprocess.check_output(['rustc','-Vv'],text=True),'lscpu':cpulines,'cpuinfo':subprocess.check_output(['lscpu'],text=True),'input_reference':'expected.json','warm_files':True}
(R/'measurement.json').write_text(json.dumps(measure,indent=2)+'\n')
groups=collections.defaultdict(list)
for line in (R/'samples.jsonl').read_text().splitlines():
    s=json.loads(line);groups[(s['workload'],s['algorithm'],s['repeat'])].append(s)
summary=[]
for (w,a,r),ss in groups.items():
    assert len(ss)==30
    summary.append({'workload':w,'algorithm':a,'repeat':r,'inside_ms':statistics.median(s['inside_ms'] for s in ss),'wall_ms':statistics.median(s['wall_ms'] for s in ss)})
summary.sort(key=lambda s:(s['workload'],s['algorithm'],s['repeat']))
(R/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
for s in summary:print(s)
