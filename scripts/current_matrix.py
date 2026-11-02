#!/usr/bin/env python3
"""Output-checked, whole-process cross-runtime matrix. Raw output is never committed."""
from pathlib import Path
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compute_matrix import port

RNX = '83d94173bbfcb5228878eb5f1d64cdb92f3c4f79'
RUNE = '2565a2a4563a915d49de061931f2951fd5dede31'
KERNELS = ['fib', 'loops', 'numeric_calls', 'awfy_sieve', 'awfy_permute',
		   'shared_rows', 'vec_iter_i64', 'vec_iter_bool',
		   'vec_append_million_i64', 'vec_append_million_bool']


def pin(path):
	path = Path(path).resolve()
	return dict(path=str(path), bytes=path.stat().st_size,
				sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def doc(path, value):
	Path(path).write_text(json.dumps(value, indent=2) + '\n')


def thermal(cpu):
	root = Path(f'/sys/devices/system/cpu/cpu{cpu}/thermal_throttle')
	return {name: int((root / name).read_text())
			for name in ['core_throttle_count', 'package_throttle_count']}


def canonical(stdout, workload):
	assert stdout.endswith(b'\n') and stdout.count(b'\n') == 1, stdout
	text = stdout.decode().strip()
	if workload == 'json':
		return json.dumps(json.loads(text), sort_keys=True, separators=(',', ':'))
	assert re.fullmatch(r'[0-9]+', text), text
	return text


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument('--build', type=Path, required=True, help='locked rnx0203 BUILD.json')
	parser.add_argument('--out', type=Path, required=True, help='new ignored raw run directory')
	parser.add_argument('--cpu', type=int, default=4)
	parser.add_argument('--julia', type=Path, required=True, help='actual Julia executable, outside juliaup')
	parser.add_argument('--julia-sysimage', type=Path, required=True)
	args = parser.parse_args()
	repo = Path(__file__).resolve().parents[1]
	out = args.out.resolve()
	out.mkdir(parents=True, exist_ok=False)
	started = time.monotonic()
	result = dict(status='FAIL')
	try:
		build = json.loads(args.build.read_text())
		assert build['status'] == 'PASS' and build['commit'] == RNX and build['rune_commit'] == RUNE
		assert pin(build['binary']['path']) == build['binary']
		binary = build['binary']['path']
		source, engine = Path(build['source']), Path(build['rune_source'])
		for path, revision in [(source, RNX), (engine, RUNE)]:
			assert subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip() == revision
			# Cargo creates an untracked .cargo-ok in its Git checkout.
			assert not subprocess.check_output(['git', '-C', str(path), 'status', '--porcelain', '--untracked-files=no'], text=True).strip()
		env = dict(os.environ, PATH=os.path.expanduser('~/.cargo/bin:~/.bun/bin:~/.deno/bin:~/.juliaup/bin:~/.local/bin').replace(':~', ':' + str(Path.home())) + ':' + os.environ['PATH'],
				   R_LIBS_USER=str(Path.home() / 'R/library'), RNX_CONFIG='', NO_COLOR='1', JULIAUP_NO_SELFUPDATE='1')
		env.pop('PERF_BUILDID_DIR', None)
		def exe(name):
			path = shutil.which(name, path=env['PATH'])
			assert path, name
			return path
		scripts = repo / 'scripts'
		node = Path.home() / 'opt/node-v22.22.1-linux-x64/bin/node'
		java = exe('java')
		kotlin = str(scripts / 'jvm/json-kotlin.jar') + ':' + str(Path.home() / 'opt/json.jar')
		rows = {}
		def row(name, bare, js, compute=None, version=None):
			rows[name] = dict(bare=bare, json=js, compute=compute, version=version)
		for name, flags in [('rnx default', []), ('rnx native off', ['--native=off']), ('rnx legacy', ['--engine=legacy'])]:
			prefix = [binary, '--color=never']
			row(name, prefix + ['run'] + flags + [str(scripts / 'bare.rn')],
				prefix + ['run'] + flags + [str(scripts / 'json.rn')],
				('rune', prefix + ['run'] + flags + ['--budget', str(2**40 - 1)]), [binary, 'version'])
		row('Bun', [exe('bun'), '-e', 'console.log(42)'], [exe('bun'), str(scripts/'json.js')], ('javascript', [exe('bun')]), [exe('bun'), '--version'])
		for name, path in [('Node official', str(node)), ('Node distro', '/usr/bin/node')]:
			row(name, [path, '-e', 'console.log(42)'], [path, str(scripts/'json.js')], ('javascript', [path]), [path, '--version'])
		row('Deno', [exe('deno'), 'eval', 'console.log(42)'], [exe('deno'), 'run', str(scripts/'json.js')], ('javascript', [exe('deno'), 'run']), [exe('deno'), '--version'])
		row('Python', [exe('python3'), '-c', 'print(42)'], [exe('python3'), '-B', str(scripts/'bench_json.py')], ('python', [exe('python3'), '-B']), [exe('python3'), '--version'])
		for module, script in [('PP', 'json.pl'), ('XS', 'json_xs.pl')]:
			row('Perl JSON::'+module, [exe('perl'), '-e', 'print "42\\n"'], [exe('perl'), str(scripts/script)], version=[exe('perl'), '-MJSON::'+module, '-e', f'print "$^V JSON::{module}=$JSON::{module}::VERSION\\n"'])
		row('Ruby', [exe('ruby'), '-e', 'puts 42'], [exe('ruby'), str(scripts/'json.rb')], version=[exe('ruby'), '--version'])
		for name, command in [('LuaJIT', exe('luajit')), ('Lua 5.4', exe('lua54'))]:
			for encoder, script in [('cjson', 'json_cjson.lua'), ('json.lua', 'json_pure.lua')]:
				row(name+' '+encoder, [command, '-e', 'print(42)'], [command, str(scripts/script)], ('lua', [command]), [command, '-v'])
		row('Kotlin jar', [java, '-jar', str(scripts/'jvm/bare-kotlin.jar')], [java, '-cp', kotlin, 'JsonKt'], version=[java, '-version'])
		row('Scala jar', [java, '-jar', str(scripts/'jvm/bare-scala.jar')], [java, '-jar', str(scripts/'jvm/json-scala.jar')], version=[java, '-version'])
		julia = str(args.julia.resolve())
		assert Path(julia).name == 'julia' and 'julialauncher' not in julia
		row('Julia', [julia, '--startup-file=no', '-e', 'println(42)'], [julia, '--startup-file=no', str(scripts/'json.jl')], version=[julia, '--version'])
		row('R', [exe('Rscript'), '-e', 'cat("42\\n")'], [exe('Rscript'), str(scripts/'json.R')], version=[exe('Rscript'), '--version'])
		kernels = source / 'tools/routing-bench/kernels'
		inputs = {}
		cells = {'bare': {}, 'json': {}}
		for name, rowdata in rows.items():
			for workload in cells:
				cells[workload][name] = rowdata[workload]
		for name in KERNELS:
			rounds = 1 if 'million' in name else 16
			root = engine/'crates/rune/src/experimental_core/region/fixtures' if 'million' in name else kernels
			rune = root/(name+'.rn')
			inputs[str(rune)] = pin(rune)
			rn = out/(name+'.rn')
			rn.write_text(rune.read_text() + f'\npub fn main(args) {{let checksum=0;for i in 0..{rounds} {{checksum=(checksum+kernel(i%97+1))%1000000007;}}checksum}}\n')
			lua_name = 'vec_iter_'+name.rsplit('_', 1)[1] if 'million' in name else name
			luafile = kernels/(lua_name+'.lua')
			inputs[str(luafile)] = pin(luafile)
			lua = luafile.read_text()
			if 'million' in name:
				assert lua.count('for i=0,9999 do') == 1
				lua = lua.replace('for i=0,9999 do', 'for i=0,999999 do')
			lu = out/(name+'.lua')
			lu.write_text(lua + f'\nlocal checksum=0 for i=0,{rounds-1} do checksum=(checksum+kernel(i%97+1))%1000000007 end io.write(string.format("%.0f\\n",checksum))\n')
			paths = {'rune': rn, 'lua': lu}
			for language, suffix in [('python', 'py'), ('javascript', 'js')]:
				content = port(name, language, rounds)
				if content is not None:
					p=out/(name+'.'+suffix)
					p.write_text(content)
					paths[language]=p
			cells[name] = {}
			for runtime, rowdata in rows.items():
				if rowdata['compute'] is not None:
					language, prefix = rowdata['compute']
					if language in paths:
						cells[name][runtime] = prefix + [str(paths[language])]
		versions = {}
		for name, rowdata in rows.items():
			p = subprocess.run(rowdata['version'], env=env, capture_output=True, timeout=30, check=True)
			versions[name] = (p.stdout + p.stderr).decode().strip()
		metadata = dict(date=datetime.datetime.now(datetime.timezone.utc).isoformat(), rnx=RNX, rune=RUNE,
						build_receipt=pin(args.build), binary=pin(binary), cpu=args.cpu,
						cpu_model=next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),
						kernel=os.uname().release, versions=versions,
						artifacts=[pin(p) for p in (scripts/'jvm').glob('*.jar')] + [pin(Path.home()/'opt/json.jar'), pin(args.julia_sysimage)],
						sources=list(inputs.values()) + [pin(p) for p in out.iterdir() if p.suffix in ['.rn','.lua','.py','.js']] + [pin(p) for p in scripts.glob('json*') if p.is_file()] + [pin(scripts/p) for p in ['bare.rn','bench_json.py','compute_matrix.py','current_matrix.py']],
						executables={p: pin(p) for p in sorted({cmd[0] for cases in cells.values() for cmd in cases.values()})},
						hyperfine=subprocess.check_output([exe('hyperfine'),'--version'],env=env,text=True).strip(),
						commands=cells, rounds={name:1 if 'million' in name else 16 for name in KERNELS})
		doc(out/'METADATA.json',metadata)
		# A lease excludes all cooperating build/measurement jobs. No readiness polling.
		with open('/tmp/rnx-runtime-bench.lock','a+') as lease:
			fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
			os.sched_setaffinity(0,{args.cpu})
			checks = {}
			for workload, cases in cells.items():
				checks[workload] = {}
				for runtime, command in cases.items():
					p=subprocess.run(command,cwd=scripts,env=env,capture_output=True,timeout=120,check=True)
					assert not p.stderr,(workload,runtime,p.stderr)
					checks[workload][runtime]=canonical(p.stdout,workload)
				values=set(checks[workload].values())
				assert len(values)==1,(workload,checks[workload])
				if workload=='bare':assert values=={'42'}
				if workload=='json':assert values=={'{"a":[9999,2,3],"b":"hello"}'}
			doc(out/'OUTPUT-CHECKS.json',dict(status='PASS',checks=checks))
			batches={}
			for workload,cases in cells.items():
				order=list(cases)
				random.Random(20261101+list(cells).index(workload)).shuffle(order)
				command=[exe('hyperfine'),'-N','--warmup','5' if workload=='bare' else '3','--runs','50' if workload=='bare' else '30','--export-json',str(out/(workload+'.json'))]
				for runtime in order:command+=['--command-name',runtime,shlex.join(cases[runtime])]
				before=thermal(args.cpu)
				with (out/(workload+'.log')).open('x') as stream:
					subprocess.run(command,cwd=scripts,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=3600)
				after=thermal(args.cpu)
				batches[workload]=dict(before=before,after=after,throttled=before!=after,command=command)
				doc(out/'BATCHES.json',batches)
			for identity in metadata['sources']+metadata['artifacts']+list(metadata['executables'].values()):
				assert pin(identity['path'])==identity,identity['path']
			result=dict(status='PASS',rnx=RNX,rune=RUNE,metadata=str(out/'METADATA.json'),checks=str(out/'OUTPUT-CHECKS.json'),batches=batches,seconds=time.monotonic()-started)
	except BaseException as error:
		result.update(error=repr(error),seconds=time.monotonic()-started)
		raise
	finally:
		doc(out/'RESULT.json',result)
		print(result['status'],str(out/'RESULT.json'),flush=True)


if __name__ == '__main__':
	main()
