import json,pathlib,statistics,math
OUT=pathlib.Path(__file__).resolve().parents[2]/'results/polars-cost-0058'
samples=json.loads((OUT/'samples.json').read_text());rss=json.loads((OUT/'rss.json').read_text())
lines=['# 0058 gate 5 observations','','Warm launches, normal Python bytecode caching. Two interleaved repeats; 30 samples per product/workload/repeat. No samples discarded. Different engine revisions: no boundary-only attribution.','','| Product | Init medians (ms) | Pipeline medians (ms) | Pipeline p95 (ms), pooled | Pipeline peak RSS median (MiB) |','| --- | --- | --- | --- | --- |']
for product in ['python','ordinary','project','generated-direct','aligned-direct']:
 groups=[[s['ms'] for s in samples if s['product']==product and s['mode']==mode and s['repeat']==repeat] for mode in ['init','pipeline'] for repeat in range(2)]
 vals=sorted(groups[2]+groups[3]);p95=vals[math.ceil(.95*len(vals))-1]
 memory=statistics.median(s['peak_rss_kib']/1024 for s in rss if s['product']==product and s['mode']=='pipeline')
 lines.append(f'| {product} | {statistics.median(groups[0]):.2f} / {statistics.median(groups[1]):.2f} | {statistics.median(groups[2]):.2f} / {statistics.median(groups[3]):.2f} | {p95:.2f} | {memory:.1f} |')
setup=json.loads((OUT/'setup.json').read_text());conditions=json.loads((OUT/'conditions.json').read_text())
lines+=['',f'Empty-target Rust build, cached downloads, two jobs: {setup["cold_seconds"]:.2f} s. Warm build: {setup["warm_seconds"]:.2f} s.',f'Private Python venv: {setup["python_venv_seconds"]:.3f} s; install exact cached wheels: {setup["python_install_seconds"]:.3f} s. No download timing.',f'Fingerprint tree bytes per launch: {conditions["input_bytes"]:,}; executable hashes and byte sizes are in conditions.json. Ancestor/config inventory is additional.', '', 'GNU time peak RSS is a separate launch observation including native threads, not a sum of concurrent process-tree RSS. Timing includes no-shell process spawn/capture/wait overhead. CSV creation, both reads, collect, write and close/flush are inside pipeline time; directory setup/removal and fsync durability are not.', '', 'The rejected preliminary no-bytecode-cache block is retained separately and contributes no samples to this table.']
(OUT/'SUMMARY.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
