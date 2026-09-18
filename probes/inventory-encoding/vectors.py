#!/usr/bin/env python3
"""Independent framing, using the accepted whole-input BLAKE3 reference."""
import json,pathlib,struct,subprocess,tempfile,sys
B=pathlib.Path(__file__).resolve().parents[2]
REF=B/'probes/hash-choice/target/release/rnx-hash-choice-probe'
assert REF.is_file(),'build the accepted hash-choice probe first'
def digest(data):
    with tempfile.NamedTemporaryFile() as f:
        f.write(data);f.flush()
        return subprocess.check_output([str(REF),'hash-reference',f.name],text=True).strip()
def tree(files):
    b=bytearray(b'rnx-tree-v2\0')
    for f in sorted(files,key=lambda f:f['path'].encode()):
        name=f['path'].encode();content=bytes.fromhex(f['hex'])
        b+=struct.pack('>Q',len(name))+name+bytes([f['executable']])+struct.pack('>Q',len(content))+bytes.fromhex(digest(content))
    return digest(b)
if __name__=='__main__':
    cases=[[],[{'path':'a','hex':'78','executable':False}],
           [{'path':'empty','hex':'','executable':False}],
           [{'path':'é/"🙂','hex':'00ff0a','executable':True},{'path':'A','hex':'6162','executable':False}],
           [{'path':'ab','hex':'63','executable':False}],
           [{'path':'a','hex':'6263','executable':False}]]
    result=[{'files':fs,'blake3':tree(fs)} for fs in cases]
    out=B.parent/'rnx/tools/project/src/fingerprint/vectors.json'
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if sys.argv[1:]==['--check']:assert out.read_text()==text
    else:
        assert not sys.argv[1:]
        out.write_text(text)
    print(out)
