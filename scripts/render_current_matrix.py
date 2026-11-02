#!/usr/bin/env python3
"""Render only a completed matrix; keep absolute paths and raw samples out of Git."""
from pathlib import Path
import argparse
import json
import math
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_matrix import KERNELS, RNX, RUNE, pin

LABELS = dict(bare='Startup', json='10k JSON', fib='fib', loops='loops',
	numeric_calls='numeric calls', awfy_sieve='sieve', awfy_permute='permute',
	shared_rows='shared rows', vec_iter_i64='list i64', vec_iter_bool='list bool',
	vec_append_million_i64='1M i64', vec_append_million_bool='1M bool')


def render(raw):
	result = json.loads((raw/'RESULT.json').read_text())
	metadata = json.loads((raw/'METADATA.json').read_text())
	checks = json.loads((raw/'OUTPUT-CHECKS.json').read_text())
	assert result['status'] == checks['status'] == 'PASS'
	assert result['rnx'] == metadata['rnx'] == RNX
	assert result['rune'] == metadata['rune'] == RUNE
	workloads = ['bare', 'json'] + KERNELS
	assert set(result['batches']) == set(workloads)
	assert set(checks['checks']) == set(workloads)
	data = {}
	for name in workloads:
		rows = json.loads((raw/(name+'.json')).read_text())['results']
		expected = metadata['commands'][name]
		assert {r['command'] for r in rows} == set(expected)
		assert set(checks['checks'][name])==set(expected)
		assert len(set(checks['checks'][name].values()))==1
		data[name] = {}
		for row in rows:
			assert len(row['times']) == (50 if name == 'bare' else 30)
			assert all(code == 0 for code in row['exit_codes'])
			assert row['mean'] > 0 and row['stddev'] >= 0
			assert all(value>0 for value in row['times'])
			for statistic, recomputed in [('mean',statistics.fmean(row['times'])),
				('stddev',statistics.stdev(row['times'])),('median',statistics.median(row['times'])),
				('max',max(row['times']))]:
				assert math.isclose(row[statistic],recomputed,rel_tol=1e-10)
			data[name][row['command']] = dict(mean_ms=row['mean']*1000,
				stddev_ms=row['stddev']*1000, median_ms=row['median']*1000,
				max_ms=row['max']*1000, samples=len(row['times']))
		raw_throttle = result['batches'][name]
		assert raw_throttle['throttled'] == (raw_throttle['before'] != raw_throttle['after'])
	versions = {k:v.replace('\n','; ') for k,v in metadata['versions'].items()}
	summary = dict(date=metadata['date'], cpu_model=metadata['cpu_model'],
		cpu=metadata['cpu'], kernel=metadata['kernel'], rnx=RNX, rune=RUNE,
		hyperfine=metadata['hyperfine'], versions=versions,
		binary_sha256=metadata['binary']['sha256'],
		artifacts=[{k:v for k,v in identity.items() if k!='path'} | {'file':Path(identity['path']).name}
			for identity in metadata['artifacts']],
		checksums={name:next(iter(set(values.values()))) for name,values in checks['checks'].items()},
		captures=[{k:v for k,v in pin(raw/name).items() if k!='path'} | {'file':name}
			for name in ['RESULT.json','METADATA.json','OUTPUT-CHECKS.json']+[name+'.json' for name in workloads]],
		operators=[{k:v for k,v in identity.items() if k!='path'} | {'file':Path(identity['path']).name}
			for identity in metadata['sources'] if Path(identity['path']).name in ('current_matrix.py','compute_matrix.py')],
		rounds=metadata['rounds'], measurements=data,
		thermal={name:{k:v for k,v in batch.items() if k!='command'}
			for name,batch in result['batches'].items()})
	names = list(metadata['commands']['bare'])
	def table(columns):
		is_compute=columns==KERNELS
		lines = ['| Runtime | ' + ' | '.join(LABELS[name]+(' †' if result['batches'][name]['throttled'] else '') for name in columns)+' |',
			'|---|'+'---:|'*len(columns)]
		for runtime in names:
			if is_compute and (not any(runtime in data[name] for name in columns) or runtime.endswith('json.lua')):
				continue
			cells = []
			for name in columns:
				measurement = data[name].get(runtime)
				cell='n/a' if measurement is None else f"{measurement['mean_ms']:.3f} ± {measurement['stddev_ms']:.3f}"
				if is_compute and name=='awfy_permute' and runtime=='LuaJIT cjson':
					cell+=' ‡'
				cells.append(cell)
			label=runtime.removesuffix(' cjson') if is_compute else runtime
			lines.append('| '+label+' | '+' | '.join(cells)+' |')
		return '\n'.join(lines)
	permute=data['awfy_permute']['LuaJIT cjson']
	footnote=f"‡ LuaJIT permute: median {permute['median_ms']:.3f} ms, maximum {permute['max_ms']:.3f} ms. "
	if permute['stddev_ms']>permute['mean_ms']:
		footnote+='Its standard deviation exceeds its mean; extreme samples dominate the mean. '
	if result['batches']['awfy_permute']['throttled']:
		footnote+='This batch also showed thermal throttling (†).'
	availability='Perl, Ruby, Kotlin, Scala, Julia and R have startup/JSON cells only. Compute uses one fixed cjson-labelled capture for each Lua runtime, without averaging the encoder-labelled duplicates.'
	def comparison(workload,other,label):
		a=round(data[workload]['rnx default']['mean_ms'],3)
		b=round(data[workload][other]['mean_ms'],3)
		if a<=b:
			return f'rnx default is {b/a:.2f}× faster than {label}'
		return f'{label} is {a/b:.2f}× faster than rnx default'
	reading=('From the rendered sample means, '+comparison('fib','rnx native off','native off')+' on fib and '+
		comparison('awfy_permute','rnx native off','native off')+' on permute. '+
		comparison('vec_iter_i64','rnx native off','native off')+' on the integer list, and '+
		comparison('vec_iter_bool','rnx native off','native off')+' on the Boolean list. '+
		'Against LuaJIT, '+comparison('fib','LuaJIT cjson','LuaJIT')+' on fib and '+
		comparison('vec_iter_i64','LuaJIT cjson','LuaJIT')+' on the integer list, while '+
		comparison('vec_iter_bool','LuaJIT cjson','LuaJIT')+' on the Boolean list. '+
		'On numeric calls, '+comparison('numeric_calls','Bun','Bun')+', '+
		comparison('numeric_calls','Node official','official Node')+', and '+
		comparison('numeric_calls','Python','Python')+'. '+
		'At startup, '+comparison('bare','LuaJIT cjson','LuaJIT')+' and '+comparison('bare','Bun','Bun')+'. '+
		'These are ratios of whole-process sample means, not confidence-bound rankings.')
	compute=table(KERNELS)+'\n\n'+availability+'\n\n'+footnote+'\n\n### Reading the tables\n\n'+reading
	return summary, table(['bare','json']), compute


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument('raw',type=Path)
	args = parser.parse_args()
	repo = Path(__file__).resolve().parents[1]
	summary, startup, compute = render(args.raw)
	stamp = summary['date'][:10]
	name = 'cross-runtime-'+stamp+'-'+RNX[:8]
	destination = repo/'results'/name
	destination.with_suffix('.json').write_text(json.dumps(summary,indent=2)+'\n')
	intro = f'''# Cross-runtime matrix, {stamp} (UTC)

Intel i7-14700, Linux {summary['kernel']}; CPU {summary['cpu']} affinity inherited by
all child threads. rnx `{RNX[:8]}`, public Rune N6 `{RUNE[:8]}`. Default native
on, native off and legacy use the same locked production binary.

Times are **whole-process milliseconds, mean ± sample standard deviation**.
Startup, compilation, native preparation and recursive first-call fallback are
included. Compute runs call each kernel 16 times (seed `i % 97 + 1`); the two
million-element cases run once. Sixteen calls make the fast compute cells partly
a startup comparison. The rnx compute commands set `--budget 1099511627775`
(`2^40-1`), rather than the CLI default of 2,000,000; other runtimes have no
equivalent work limit. JSON and startup use the default budget.

Hyperfine `-N` executes without a shell: 5 warmups/50 samples for startup,
3 warmups/30 samples for JSON and compute. Startup evaluates **and prints** 42;
the JSON programs serialize 10,000 times and print the last value. Before any
timing, every included program exits 0, prints one line, and matches the other
implementations (sorted-key canonical JSON, otherwise an integer checksum).
JavaScript numbers stay within the exact-integer range on these inputs; Rune
additionally enforces checked integers and a work budget.

**† marks a thermally throttled batch**, from before/after core or package
throttle counters. Those wall times describe that session, with reduced
confidence in comparisons. No batches are silently replaced. CPU affinity
penalizes runtimes with parallel JIT/GC work, including JVM, Julia, Deno and Bun.
The ± values show observed spread, not a confidence interval or proof of a rank.
There is no aggregate score.

## Startup and JSON

Encoder choices and APIs differ; these timings do not isolate implementation
language. Lua and Perl rows retain both encoders. Node official and distro
builds are separate even when their version strings agree.
Lua's encoder suffix applies only to JSON; its compute programs do not call an
encoder. The compute table uses the fixed cjson-labelled sample set for each Lua
runtime, with duplicate encoder-labelled samples excluded from that table.

'''
	notes = '''

## Compute

`n/a` means no matching port in this refresh, not a failure or estimated time.
Lua pairs come from the pinned routing sources; JavaScript/Python ports cover
only simple scalar and list kernels. The million-element Lua sources use the
same list algorithm with its construction count changed from 10,000 to 1,000,000.
Each list case includes **both construction and eight reads**, rather than
claiming a separately timed append-only operation.

Native regions cover admitted scalar loops, homogeneous integer/Boolean list
reads/writes/iteration/appends, and scalar direct self recursion. `fib` and
numeric/list kernels use those paths. Sieve combines native list loops with
interpreted surrounding methods. Recursive first calls can replay in the
interpreter until sufficient engine stack room exists; later calls can complete
native. That first-call behavior is included here. Permute uses a guarded named
receiver with scalar fields, one integer list, closed helpers and self recursion;
its setup and verification stay interpreted. `shared_rows` keeps its string/table
search in the interpreter.

'''
	versions = '\n\n## Versions and provenance\n\n'
	versions += '\n'.join('- **'+name+'**: '+version.replace('|','\\|') for name,version in summary['versions'].items())
	versions += f'''

Kotlin/Scala are precompiled jars on the listed JVM, so source compilation is
excluded but JVM startup/JIT is included. Jar hashes, binary hash, versions,
round counts, sample summaries and thermal counters are retained in the
[machine-readable summary]({name}.json). The Kotlin/Scala source
and build instructions are in [scripts/jvm](../scripts/jvm/README.md).
These rows describe the identified artifacts, not arbitrary installations.

Rerun from the repository root after building the pinned production CLI with
the normal locked feature set and retaining its BUILD.json (commit, Rune pin,
clean source directories, executable hash/size):

```sh
python3 -I -B scripts/build_matrix_rnx.py target/readme-n6-build
export JULIAUP_NO_SELFUPDATE=1
JULIA_REAL="$(julia --startup-file=no -e 'print(joinpath(Sys.BINDIR,Base.julia_exename()))')"
JULIA_SYSIMAGE="$(julia --startup-file=no -e 'print(unsafe_string(Base.JLOptions().image_file))')"
python3 -I -B scripts/current_matrix.py --build target/readme-n6-build/BUILD.json --out target/readme-n6-new-run --julia "$JULIA_REAL" --julia-sysimage "$JULIA_SYSIMAGE"
python3 -I -B scripts/render_current_matrix.py target/readme-n6-new-run
```

The harness uses the exact Rune/rnx sources named by that receipt, installed
runtimes on PATH, the official Node binary at `~/opt/node-v22.22.1-linux-x64/bin/node`,
`~/opt/json.jar`, and the prebuilt JVM jars. The old shell runners remain
available for the dated suites. New raw hyperfine JSON, validation output,
commands, complete input hashes and logs live only in the ignored run directory;
the compact summary is committed. Rendering validates successful terminal
receipts and sample counts before replacing tables or README content.
'''
	destination.with_suffix('.md').write_text(intro+startup+notes+compute+versions)
	readme = repo/'README.md'
	text = readme.read_text()
	start, end = '<!-- current-matrix:start -->', '<!-- current-matrix:end -->'
	assert text.count(start)==text.count(end)==1
	a,b=text.index(start)+len(start),text.index(end)
	block = '\n\n'+startup+'\n\n'+compute+f'\n\n† = thermally throttled batch; n/a = no matching port. All cells are milliseconds,\nmean ± sample standard deviation. [Conditions, versions and provenance](results/{name}.md).\n\n'
	readme.write_text(text[:a]+block+text[b:])
	print('PASS',destination.with_suffix('.md'))


if __name__=='__main__':
	main()
