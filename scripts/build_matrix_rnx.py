#!/usr/bin/env python3
"""Build the exact published production CLI and emit a matrix build receipt."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
from current_matrix import RNX, RUNE, pin, doc


def main():
	parser=argparse.ArgumentParser(description=__doc__)
	parser.add_argument('out',type=Path,help='new build directory')
	args=parser.parse_args()
	out=args.out.resolve()
	out.mkdir(parents=True,exist_ok=False)
	source=out/'source'
	env=dict(os.environ,CARGO_TARGET_DIR=str(out/'target'),CARGO_BUILD_JOBS='4',CARGO_INCREMENTAL='0')
	cargo=['cargo','+1.98.1']
	commands=[]
	started=time.monotonic()
	result=dict(status='FAIL',commit=RNX,rune_commit=RUNE)
	def run(command,log,cwd=None):
		commands.append(command)
		with(out/log).open('x')as stream:
			subprocess.run(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
	try:
		run(['git','clone','--no-checkout','https://github.com/nilket-com/rnx.git',str(source)],'clone.log')
		run(['git','-C',str(source),'checkout','--detach',RNX],'checkout.log')
		run(cargo+['fmt','--all','--check'],'format.log',source)
		run([sys.executable,'-I','-B','tools/test_verify_pins.py'],'pins.log',source)
		command=cargo+['build','--release','--locked','--bin','rnx','--message-format=json-render-diagnostics']
		run(command,'build.jsonl',source)
		artifacts=[]
		for line in(out/'build.jsonl').read_text().splitlines():
			try:
				message=json.loads(line)
			except ValueError:
				continue
			if message.get('reason')=='compiler-artifact':
				artifacts.append(message)
		engine=[m for m in artifacts if m['target']['name']=='rune']
		product=[m for m in artifacts if m.get('executable')==str(out/'target/release/rnx')]
		assert len(engine)==len(product)==1
		assert set(engine[0]['features'])=={'alloc','anyhow','execution','fmt','native-code','serde','std'}
		rune_source=Path(engine[0]['target']['src_path']).parents[3]
		assert subprocess.check_output(['git','-C',str(rune_source),'rev-parse','HEAD'],text=True).strip()==RUNE
		metadata=json.loads(subprocess.check_output(cargo+['metadata','--locked','--offline','--format-version','1'],cwd=source,env=env))
		packages=[p for p in metadata['packages']if p['name']=='rune']
		assert len(packages)==1 and packages[0]['source'].endswith('#'+RUNE)
		assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
		result.update(status='PASS',source=str(source),rune_source=str(rune_source),
			binary=pin(out/'target/release/rnx'),features=engine[0]['features'],
			product_features=product[0]['features'],
			toolchain=subprocess.check_output(cargo+['--version'],text=True).strip())
	except BaseException as error:
		result.update(error=repr(error))
		raise
	finally:
		result.update(commands=commands,seconds=time.monotonic()-started)
		doc(out/'BUILD.json',result)
		print(result['status'],out/'BUILD.json',flush=True)


if __name__=='__main__':
	main()
