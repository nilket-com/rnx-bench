#!/usr/bin/env python3
"""Check the documented public inventory and compile forbidden imports."""
import pathlib,re,json,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
RNX=ROOT.parent/'rnx';OUT=ROOT/'results/extensions-0051'
html=(RNX/'target/doc/rnx/index.html').read_text()
sections=re.findall(r'<h2 id="([^"]+)" class="section-header">',html)
assert sections==['reexports','structs','functions'],sections
structs=set(re.findall(r'href="struct\.([^".]+)\.html"',html))
functions=set(re.findall(r'href="fn\.([^".]+)\.html"',html))
assert structs=={'Extensions'} and functions=={'main_with'},(structs,functions)
assert 'rune' in html
results={'documented':{'structs':sorted(structs),'functions':sorted(functions),'reexports':['rune']},'compilation':{}}
with tempfile.TemporaryDirectory(prefix='rnx public api ') as d:
    d=pathlib.Path(d)
    cases={'public':'use rnx::{main_with, Extensions, rune}; fn check() { let _ = main_with; let _ = Extensions::none(); let _ = rune::Module::new(); }'}
    for name in ['install_core','session','runner','worker','config','memory','host','extensions','VERSION']:
        cases[name]=f'use rnx::{name};'
    cases['fields']='fn check(e: rnx::Extensions) { let _ = e.builders; }'
    for name,source in cases.items():
        path=d/(name+'.rs');path.write_text(source)
        command=['rustc','--edition=2024','--crate-type=lib','--emit=metadata','--crate-name','api_probe',str(path),'--extern',f'rnx={RNX}/target/release/librnx.rlib','-L',f'dependency={RNX}/target/release/deps','-o',str(d/'probe.rmeta')]
        r=subprocess.run(command,capture_output=True,text=True)
        results['compilation'][name]={'source':source,'exit':r.returncode,'stderr':r.stderr}
        assert (r.returncode==0)==(name=='public'),(name,r.stderr)
        if name!='public':assert 'private' in r.stderr,(name,r.stderr)
(OUT/'api.json').write_text(json.dumps(results,indent=2)+'\n')
print('documented inventory and external compile-time boundary passed')
