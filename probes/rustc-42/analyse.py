"""Reproduce every timing table from the retained commands and raw ns samples."""
import collections,json,pathlib,statistics,sys
O=pathlib.Path(sys.argv[1])
c=json.loads((O/'conditions.json').read_text())
selected=json.loads((O/'selected-affinity-control.json').read_text())
rows=[json.loads(s) for s in (O/'samples.jsonl').read_text().splitlines()]
by=collections.defaultdict(list)
seen=set()
for r in rows:
	key=(r['case'],r['repeat'],r['sample']);assert key not in seen,key;seen.add(key)
	assert type(r['ns']) is int and r['ns']>0,r
	assert r['repeat'] in range(3) and r['sample'] in range(30),r
	if r['case'] in c['cases']:
		assert r['group']==c['cases'][r['case']]['group'],r
	else:
		assert r['case'] in ('human-unpinned','four-cores') and r['selected']==selected['case'],r
	by[r['case']].append(r)
assert set(by)==set(c['cases'])|{'human-unpinned','four-cores'}
assert all(len(v)==90 for v in by.values())
def stats(rs):
	d=sorted(r['ns']/1e6 for r in rs)
	return dict(n=len(d),mean=statistics.mean(d),min=d[0],median=statistics.median(d),p10=d[int(.10*(len(d)-1))],p90=d[int(.90*(len(d)-1))],p95=d[int(.95*(len(d)-1))],under={str(t):sum(v<t for v in d) for t in c['frame_threshold_ms']})
s={k:stats(v) for k,v in by.items()}
rounds={k:{str(i):stats([r for r in v if r['repeat']==i]) for i in range(3)} for k,v in by.items()}
(O/'summary.json').write_text(json.dumps({'aggregate':s,'rounds':rounds},indent=2)+'\n')
def table(names,frames=False):
	head='| Configuration | Mean ms | Min | Median | p95 |'
	if frames:head+=' <16.7 ms | <8.3 ms | <6.9 ms |'
	else:head+=' p10–p90 |'
	out=[head,'|'+ '|'.join(['---']*(8 if frames else 6))+'|']
	for name in names:
		a=s[name];line=f"| {name} | {a['mean']:.3f} | {a['min']:.3f} | {a['median']:.3f} | {a['p95']:.3f} |"
		if frames:line+=' '+ ' | '.join(f"{a['under'][str(t)]}/90 ({100*a['under'][str(t)]/90:.0f}%)" for t in c['frame_threshold_ms'])+' |'
		else:line+=f" {a['p10']:.3f}–{a['p90']:.3f} |"
		out.append(line)
	return '\n'.join(out)
full=[n for n in c['cases'] if c['cases'][n]['group']=='full-build']
fastest=selected['case']
assert fastest==min(full,key=lambda n:s[n]['median'])
md='# Bare rustc and the 42 test\n\n'
md+='Quoted claim: “if you just use bare rustc you often don\'t even have compile times above your terminals refresh rate”. No tweet URL or author was supplied; this tests that quoted timing claim on this machine.\n\n'
md+='The columns below use the requested rounded frame budgets: 16.7 ms (60 Hz), 8.3 ms (120 Hz), 6.9 ms (144 Hz). “Often” has no defined frequency; the observed fraction is reported instead of silently defining it. Every row has 90 fresh invocations. These are compile **and link** timings, excluding execution.\n\n'
md+=table(full+['human-unpinned','four-cores'],True)+'\n\n'
md+=f"The last two rows repeat the fastest pinned full-build configuration, `{fastest}`, without affinity restriction and on four cores. They are later controls, not interleaved comparisons with the initial run. The fastest row was selected on the measured data; it is descriptive, not an independent performance test.\n\n"
below=sum(s[n]['under']['16.7'] for n in full+['human-unpinned','four-cores'])
count=90*(len(full)+2)
md+=f"For complete executable builds on this machine, **{below}/{count}** samples finished within the rounded 60 Hz frame budget. The quoted below-refresh claim was not observed for any tested full-build configuration. Stage-only emission does often meet that budget here; it skips some required work and cannot run. This does not establish how frequently the claim holds on other machines or for other programs.\n\n"
md+='The unpinned median (57 ms) is 2.4× the same configuration pinned to one core (24 ms), and slower than four cores (23 ms); on this hybrid i7-14700, scheduling onto E-cores or migration is a plausible but unmeasured explanation, and the unpinned case represents ordinary unrestricted invocation.\n\n'
md+='## Source to answer\n\nEvery program here prints exactly `42\\n`. Rust compiles and links on every sample, then starts the new executable. The runtimes parse/compile their input during startup. Source writing and output deletion are outside the clock. No binary reuse is credited to Rust in this table.\n\n'
md+=table([n for n in c['cases'] if c['cases'][n]['group'] in ('compile-and-run','source-to-answer')])+'\n\n'
md+='## Stages and existing binaries\n\nMetadata emission does not produce an executable; object emission skips linking. These are diagnostic paths, not source-to-answer alternatives. Existing-executable rows include process startup and printing but **exclude compilation**. `/bin/true` and compiler-version rows are overhead observations; no subtraction is applied.\n\n'
md+=table([n for n in c['cases'] if c['cases'][n]['group'] in ('compile-stage','existing-executable','overhead')],True)+'\n\n'
md+='## Clock audit\n\nThe deciding dataset is `native-final/`: a dependency-free Rust clock helper measures all compiler and interpreter commands inside the same native spawn/capture/blocking-wait interval. Preflight median `/bin/true` was 0.317 ms versus hyperfine 0.240, and cached Rust 0.381 versus 0.353; both passed the pre-agreed ±0.15 ms sanity bound. The original polling-Python dataset is retained at this directory’s parent, and the blocking-Python replay in `blocking-final/`. The latter failed the sanity bound (true 0.499 ms); neither is used for the deciding fast-runtime rankings. The independent 50-sample `hyperfine.json` is also retained. No overhead subtraction or sample removal is applied.\n\n'
md+='## What was measured\n\n'
md+='- Standalone stable rustc 1.98.1, invoked at its real toolchain path; no Cargo or rustup launcher in timed commands, no dependencies, LTO, or incremental compilation. Output is deleted before each fresh compile; the filesystem and compiler/standard-library pages are warm, not cold disk.\n'
md+='- Intel i7-14700, Linux; affinity core '+str(c['machine']['cpu'])+'. Governor `'+str(c['machine']['governor'])+'`, driver `'+str(c['machine']['driver'])+'`, min/max kHz '+str(c['machine']['min_khz'])+'/'+str(c['machine']['max_khz'])+', intel no_turbo='+str(c['machine']['intel_no_turbo'])+'. Governor names alone do not state actual clock frequency.\n'
md+='- Five warmups, three seeded shuffled rounds of 30 samples per row. Synchronous spawn/capture/wait, no shell, identical driver for each tool. In the deciding native-clock run, argument preparation, helper startup, output/status validation and serialization are outside the timer; child process spawn, pipe capture and blocking waits are inside it. Means, min, median, p95 and p10/p90 are retained; raw samples and per-round summaries are in JSON.\n'
md+='- Full builds cross three inputs and eight configurations. `empty` is `fn main(){}`; `print` uses println; `exit` exits with 42 and avoids printing. Default has no explicit optimization flag; `O` means `-O`, dynamic means `-C prefer-dynamic`, cgu1 means `-C codegen-units=1`. Exact commands are retained.\n'
md+='- Dynamic-standard-library executable checks run with its toolchain library directory in LD_LIBRARY_PATH (same environment for all rows); this is an explicit configuration, not the default bare command. Every executable was checked before timing. Linker identification per executable is retained in conditions.json. Stable output reports bundled LLD 22.1.8; no separate mold/ld.lld was found on PATH and nothing was installed.\n'
md+='- Stable exec/thread attribution is untimed under strace. Installed nightly time-passes is supplemental attribution from a different compiler, not a decomposition of the stable wall-time samples. Those diagnostics cannot be subtracted from the primary results.\n'
md+='- This tiny startup/compile workload says nothing about application throughput or large builds. Empty Rust and unused literals can be optimized away; this is not an arithmetic benchmark. Results on other hardware, toolchains, operating systems or linkers are unmeasured. The follow-up about LTO while building an interpreter concerns a different workload and is outside this probe.\n'
(O/'summary.md').write_text(md)
print(f'validated {len(rows)} samples across {len(by)} cases; tables reproduced')
