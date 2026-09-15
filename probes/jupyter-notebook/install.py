from common import *
e=Environment()
try:
    p=e.install();assert p.returncode==0,(p.stdout,p.stderr)
    spec=e.root/'data/kernels/rnx/kernel.json';before=spec.read_bytes();value=json.loads(before)
    assert value['argv']==[str(e.kernel),'--connection-file','{connection_file}','--rnx',str(e.worker)]
    assert value['display_name']=='Rune (rnx)' and value['interrupt_mode']=='message'
    p=e.install();assert p.returncode!=0 and '--replace' in p.stderr;assert spec.read_bytes()==before
    value['display_name']='Old fixture';spec.write_text(json.dumps(value));before=spec.read_bytes()
    p=e.install();assert p.returncode!=0 and spec.read_bytes()==before
    p=e.install(True);assert p.returncode==0,p.stderr;assert json.loads(spec.read_text())['display_name']=='Rune (rnx)'
    # Even an invalid spec omitted from discovery is not replaced by default.
    spec.write_text('not JSON');p=e.install();assert p.returncode!=0 and spec.read_text()=='not JSON'
    assert e.install(True).returncode==0
    p=subprocess.run([str(e.kernel),'install','--rnx','relative'],env=e.env,capture_output=True,text=True);assert p.returncode!=0 and 'absolute' in p.stderr
    bad=os.fsencode(e.bin)+b'/\xff';open(bad,'wb').close()
    p=subprocess.run([os.fsencode(e.kernel),b'install',b'--rnx',bad],env=e.env,capture_output=True);assert p.returncode!=0 and b'non-Unicode' in p.stderr and b'\\xFF' in p.stderr,p.stderr
    env=e.env.copy();env['PATH']=str(e.root/'no-cli')
    p=subprocess.run([str(e.kernel),'install','--rnx',str(e.worker)],env=env,capture_output=True,text=True);assert p.returncode!=0 and 'Jupyter CLI' in p.stderr
    log('installation_spaces_refusal_replace_invalid_spec_nonunicode_missing_cli',passed=True)
finally:e.close()
