#!/usr/bin/env python3
"""Build a private test target from an exact rnx archive; never modify rnx."""
import hashlib, json, os, pathlib, shutil, subprocess, tempfile, tomllib
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]/'rnx'
def main():
    head=subprocess.check_output(['git','-C',ROOT,'rev-parse','HEAD'],text=True).strip()
    with tempfile.TemporaryDirectory(prefix='rnx-http-build-') as tmp:
        tree=pathlib.Path(tmp)
        subprocess.run(['tar','-x','-C',tree],input=subprocess.check_output(['git','-C',ROOT,'archive',head]),check=True)
        shutil.copyfile(HERE/'probe.rs',tree/'src/server_http_probe.rs')
        shutil.copyfile(HERE/'pool.rs',tree/'src/server_pool_probe.rs')
        with (tree/'src/lib.rs').open('a') as f:f.write('\n#[cfg(test)]\nmod server_http_probe;\n')
        manifest=(tree/'Cargo.toml').read_text().replace('[dev-dependencies]', '''[dev-dependencies]
tokio-postgres = "=0.7.18"
hyper = { version = "=1.11.1", default-features = false, features = ["server", "http1"] }
hyper-util = { version = "=0.1.20", default-features = false, features = ["tokio"] }
http-body-util = "=0.1.5"
bytes = "1"
tokio = { version = "1", default-features = false, features = ["rt", "time", "net", "sync", "macros"] }
''')
        (tree/'Cargo.toml').write_text(manifest)
        # Keep the probe's resolved graph stable on subsequent builds.
        if (HERE/'Cargo.lock').exists(): shutil.copyfile(HERE/'Cargo.lock',tree/'Cargo.lock')
        env=os.environ.copy();env['CARGO_TARGET_DIR']=str(HERE/'target')
        cmd=['cargo','test','--release','--features','test-support','--lib','--no-run','--message-format=json']
        if (HERE/'Cargo.lock').exists():
            cmd.append('--offline')
            if not os.environ.get('RNX_RESOLVE_PROBE_LOCK'):cmd.append('--locked')
        result=subprocess.run(cmd,cwd=tree,env=env,text=True,stdout=subprocess.PIPE)
        for line in result.stdout.splitlines():
            j=json.loads(line)
            if j.get('reason')=='compiler-message': print(j['message'].get('rendered',''))
        result.check_returncode()
        binaries=[j['executable'] for line in result.stdout.splitlines() if (j:=json.loads(line)).get('executable')]
        assert len(binaries)==1,binaries
        shutil.copyfile(tree/'Cargo.lock',HERE/'Cargo.lock')
        metadata=json.loads(subprocess.check_output(['cargo','metadata','--locked','--offline','--format-version','1'],cwd=tree,env=env,text=True))
        packages=[{'name':p['name'],'version':p['version'],'license':p['license'],'source':p['source']} for p in metadata['packages']]
        graph={'packages':packages,'resolve':metadata['resolve']}
        (HERE/'graph.json').write_text(json.dumps(graph,indent=2).replace(str(tree),'<rnx-archive>')+'\n')
        baseline={(p['name'],p['version']) for p in tomllib.loads((ROOT/'Cargo.lock').read_text())['package']}
        linux=json.loads(subprocess.check_output(['cargo','metadata','--locked','--offline','--format-version','1','--filter-platform','x86_64-unknown-linux-gnu'],cwd=tree,env=env,text=True))
        linux_ids={n['id'] for n in linux['resolve']['nodes']}
        added=[p for p in metadata['packages'] if p['id'] in linux_ids and (p['name'],p['version']) not in baseline]
        notice=['# Additional prototype dependency notices','',
            'The archived rnx tree carries its own THIRD-PARTY-NOTICES.md. This file',
            'adds the crate-shipped licence texts of packages introduced in this Linux probe.',
            'graph.json inventories the full resolved graph (including dev, proc-macro',
            'and non-Linux packages) and its declared SPDX expressions. No binary is',
            'distributed by this source-only probe.','']
        for p in added:
            notice.extend([f"## {p['name']} {p['version']}",'',p['license'],''])
            files=sorted(f for f in pathlib.Path(p['manifest_path']).parent.iterdir() if f.is_file() and f.name.lower().startswith(('license','licence','copying','notice')))
            assert files,p['name']
            for f in files:notice.extend([f'### {f.name}','',f.read_text(),''])
        (HERE/'ADDITIONAL-NOTICES.md').write_text('\n'.join(notice))
        sources={}
        for p in metadata['packages']:
            if p['name']=='hyper':
                for name in ['src/server/conn/http1.rs','src/proto/h1/decode.rs','src/proto/h1/io.rs']:
                    sources[name]=hashlib.sha256((pathlib.Path(p['manifest_path']).parent/name).read_bytes()).hexdigest()
        conditions={'root':head,'pool_sha256':hashlib.sha256((HERE/'pool.rs').read_bytes()).hexdigest(),'hyper_sources':sources,'builder_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'graph_sha256':hashlib.sha256((HERE/'graph.json').read_bytes()).hexdigest(),'binary':binaries[0],'binary_sha256':hashlib.sha256(pathlib.Path(binaries[0]).read_bytes()).hexdigest(),'probe_sha256':hashlib.sha256((HERE/'probe.rs').read_bytes()).hexdigest(),'lock_sha256':hashlib.sha256((HERE/'Cargo.lock').read_bytes()).hexdigest(),'rustc':subprocess.check_output(['rustc','-Vv'],text=True),'manifest':manifest,'command':cmd}
        (HERE/'build.json').write_text(json.dumps(conditions,indent=2)+'\n')
        print(binaries[0])
if __name__=='__main__':main()
