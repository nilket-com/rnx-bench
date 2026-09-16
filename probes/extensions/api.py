#!/usr/bin/env python3
"""Check the documented public inventory and compile forbidden imports."""
import pathlib,re,json,subprocess,tempfile,os
ROOT=pathlib.Path(__file__).resolve().parents[2]
RNX=ROOT.parent/'rnx';OUT=pathlib.Path(os.environ.get('RNX_API_OUT', str(ROOT/'results/lifecycle-0053'))); OUT.mkdir(parents=True,exist_ok=True)
html=(RNX/'target/doc/rnx/index.html').read_text()
sections=re.findall(r'<h2 id="([^"]+)" class="section-header">',html)
assert sections==['reexports','structs','functions'],sections
structs=set(re.findall(r'href="struct\.([^".]+)\.html"',html))
functions=set(re.findall(r'href="fn\.([^".]+)\.html"',html))
assert structs=={'Extensions','Scope'} and functions=={'main_with'},(structs,functions)
assert 'rune' in html
results={'documented':{'structs':sorted(structs),'functions':sorted(functions),'reexports':['rune']},'compilation':{}}
with tempfile.TemporaryDirectory(prefix='rnx public api ') as d:
    d=pathlib.Path(d)
    cases={'public':'use rnx::{main_with, Extensions, Scope, rune}; fn check() { let _ = main_with; let _ = Extensions::none(); let _ = rune::Module::new(); }'}
    for name in ['install_core','session','runner','worker','config','memory','host','extensions','lifecycle','VERSION']:
        cases[name]=f'use rnx::{name};'
    cases['scope_fields']='fn check(s: rnx::Scope) { let _ = s.id; }'
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
