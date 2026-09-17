#!/usr/bin/env python3
"""Ordinary (no test-support) CLI ignores the compiled-out fault hooks."""
import json,os,pathlib,subprocess,tempfile
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1];ROOT=BENCH.parent/'rnx';OUT=BENCH/'results/project-workflow-0057'
with tempfile.TemporaryDirectory(prefix='rnx-project-ordinary-') as t:
    root=pathlib.Path(t);(root/'main.rn').write_text('pub fn main(_) {42}\n')
    (root/'rnx.toml').write_text('format=1\n[application]\nentry="main.rn"\n[executable]\npath='+json.dumps(str(ROOT/'target/release/rnx'))+'\n')
    marker=root/'.rnx/hook'
    env={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST','RNX_'))};env.update(TERM='xterm',NO_COLOR='1',RNX_PROJECT_PAUSE='after-cargo-publication',RNX_PROJECT_PAUSE_FILE=str(marker),RNX_PROJECT_FAIL='after-json-publication')
    tool=ROOT/'tools/project/target/debug/rnx-project'
    for command in ['lock','run']:
        p=subprocess.run([str(tool),command,'--manifest',str(root/'rnx.toml')],env=env,capture_output=True,text=True,timeout=10)
        assert p.returncode==0,(command,p.stdout,p.stderr)
        if command=='run':assert p.stdout=='42\n'
    assert not marker.exists()
(OUT/'ordinary.json').write_text(json.dumps({'ordinary_build':True,'test_hooks_absent':True,'override_result':42},indent=2)+'\n')
print('PASS ordinary CLI, compiled-out hooks and override run')
