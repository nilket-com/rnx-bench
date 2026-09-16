#!/usr/bin/env python3
"""Run a private test module against an exact isolated rnx snapshot."""
import argparse, hashlib, json, os, pathlib, shutil, subprocess, tempfile, signal
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]/'rnx'
def run(cmd, **kwargs):
    return subprocess.run(list(map(str,cmd)), check=True, text=True, **kwargs)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=pathlib.Path,required=True);ap.add_argument('--cpus',default='2,4');args=ap.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    with tempfile.TemporaryDirectory(prefix='rnx-server-assembly-') as temporary:
        tree=pathlib.Path(temporary)/'rnx';tree.mkdir()
        archive=subprocess.check_output(['git','-C',str(ROOT),'archive',head])
        p=subprocess.run(['tar','-x','-C',str(tree)],input=archive,check=True)
        patch=subprocess.check_output(['git','-C',str(ROOT),'diff','--no-color','HEAD','--binary']); subprocess.run(['git','apply','--unsafe-paths','--allow-empty','-'],cwd=tree,input=patch,check=True)
        (out/'working-tree.patch').write_bytes(patch)
        shutil.copyfile(HERE/'assembly.rs',tree/'src/server_assembly_probe.rs')
        with (tree/'src/lib.rs').open('a') as f:f.write('\n#[cfg(test)]\nmod server_assembly_probe;\n')
        with (tree/'src/execute.rs').open('a') as f:f.write('\n#[cfg(test)]\nimpl Runtime { pub(crate) fn probe_inner(&self) -> &tokio::runtime::Runtime { self.inner() } }\n')
        env={k:v for k,v in os.environ.items() if k.lower() not in ('http_proxy','https_proxy','all_proxy','no_proxy') and k!='RNX_CONFIG'}
        env.update(CARGO_TARGET_DIR=str(HERE.parent/'server-assembly/target'),RNX_ASSEMBLY_RESULTS=str(out/'results.jsonl'),TERM='dumb')
        (out/'results.jsonl').write_text('')
        command=['taskset','-c',args.cpus,'cargo','test','--release','--locked','--offline','--features','test-support','--lib','server_assembly_probe::assembly_gate','--','--ignored','--nocapture','--test-threads=1']
        with (out/'run.log').open('w') as log:
            p=subprocess.Popen(command,cwd=tree,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try: code=p.wait(timeout=240)
            except BaseException:
                os.killpg(p.pid,signal.SIGKILL);p.wait();raise
            if code: raise RuntimeError(f'probe failed: {out}/run.log')
        executables=list((HERE.parent/'server-assembly/target/release/deps').glob('rnx-*'))
        binaries={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in executables if p.is_file() and os.access(p,os.X_OK) and p.suffix!='.d'}
        conditions=dict(root=head,cpus=args.cpus,harness_sha256=hashlib.sha256((HERE/'assembly.py').read_bytes()).hexdigest(),source_sha256=hashlib.sha256((HERE/'assembly.rs').read_bytes()).hexdigest(),lock_sha256=hashlib.sha256((tree/'Cargo.lock').read_bytes()).hexdigest(),binaries=binaries,command=command,rustc=subprocess.check_output(['rustc','-Vv'],text=True),cpu=subprocess.check_output(['lscpu'],text=True))
        (out/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
    assert not pathlib.Path(temporary).exists()
    print(f'completed: {out}')
if __name__=='__main__':main()
