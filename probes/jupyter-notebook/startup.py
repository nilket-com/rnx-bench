# Historical identical-binary check at the 0047 supervision hash below.
# Deliberately keeps that revision's host:: source. For current binaries and
# namespace changes use probes/namespaces/measure.py, with separate variants.
"""Matched ordinary-rnx copies: the accepted worker hash must still be identical."""
import hashlib,shlex
from common import *
source=ROOT.parent/'rnx/target/release/rnx'
accepted=json.loads((ROOT/'results/jupyter-0047-supervision/source-and-binary-sha256.json').read_text())['../rnx/target/release/rnx']['sha256']
assert hashlib.sha256(source.read_bytes()).hexdigest()==accepted
with tempfile.TemporaryDirectory(prefix='rnx startup ') as d:
    root=pathlib.Path(d);before=root/'before-rnx';shutil.copy2(source,before)
    script=root/'bare.rn';script.write_text('pub fn main(_) { 42 }\n')
    cases=[['version'],['help'],['eval','42'],['run',str(script)],['eval','host::json_stringify(#{a: [1,2], b: "value"})?']]
    for args in cases:
        old=subprocess.run([str(before),*args],capture_output=True)
        new=subprocess.run([str(source),*args],capture_output=True)
        assert (old.returncode,old.stdout,old.stderr)==(new.returncode,new.stdout,new.stderr)
    commands=[]
    for args in [cases[0],cases[2],cases[3]]:
        for label,binary in [('accepted-copy',before),('current',source)]:
            commands += ['--command-name',label+' '+args[0],shlex.join(['taskset','-c','4',str(binary),*args])]
    subprocess.run(['hyperfine','-N','--warmup','10','--runs','100','--export-json',str(OUT/'rnx-startup.json'),*commands],check=True)
    log('ordinary_rnx_bytes_and_startup',byte_cases=len(cases),accepted_sha256=accepted,identical_binaries=True)
