"""Verify the isolated candidate without modifying the root product."""
from pathlib import Path
import subprocess as sp, json, hashlib, os
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';P=H/'target/tool';O=Path(os.environ.get('RNX_REMOVAL_RESULTS',str(B/'results/removal-ownership-0066'))).resolve();O.mkdir(parents=True,exist_ok=True)
rows=[]
for label,args in [
    ('fmt-check',['cargo','fmt','--manifest-path',P/'Cargo.toml','--','--check']),
    ('test-default',['cargo','test','--locked','--offline','--manifest-path',P/'Cargo.toml','--','--test-threads=1']),
    ('test-support',['cargo','test','--locked','--offline','--manifest-path',P/'Cargo.toml','--features','test-support','--','--test-threads=1']),
    ('clippy-support',['cargo','clippy','--locked','--offline','--manifest-path',P/'Cargo.toml','--all-targets','--features','test-support','--','-D','warnings']),
    ('clippy-default-all',['cargo','clippy','--locked','--offline','--manifest-path',P/'Cargo.toml','--all-targets','--','-D','warnings']),
]:
    with (O/(label+'.log')).open('w') as f:p=sp.run(list(map(str,args)),stdout=f,stderr=sp.STDOUT)
    assert p.returncode==0,(O/(label+'.log')).read_text();rows.append(dict(check=label,status=0));print('PASS',label,flush=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((O/'source.json').read_text())
assert all(sha(R/'tools/project'/p)==v and sha(P/p)==v for p,v in source['source_sha256'].items())
assert (P/'Cargo.lock').read_bytes()==(R/'tools/project/Cargo.lock').read_bytes()
assert sha(H/'removal_probe.rs')==source['candidate_sha256']
assert sp.check_output(['git','-C',R,'diff',source['baseline'],'--','src','Cargo.toml','Cargo.lock','tools/project','jupyter','adapters','servers'])==b''
(O/'checks.json').write_text(json.dumps(dict(checks=rows,product_unchanged=True,original_sources_identical=True,lock_identical=True),indent=2)+'\n')
