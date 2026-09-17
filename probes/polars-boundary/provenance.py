#!/usr/bin/env python3
"""Capture release, wheel and Cargo provenance without equating version labels."""
import hashlib,json,pathlib,subprocess,urllib.request,zipfile
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1];OUT=BENCH/'results/polars-boundary-0058'
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'rnx-0058-probe'})
    with urllib.request.urlopen(req,timeout=60) as r:return r.read()
def js(url):return json.loads(fetch(url))
def sha(data):return hashlib.sha256(data).hexdigest()
metadata=json.loads(subprocess.check_output(['cargo','metadata','--locked','--offline','--format-version','1','--manifest-path',str(HERE/'Cargo.toml')]))
packages=[{k:p[k] for k in ['id','name','version','source','license','license_file','manifest_path']} for p in metadata['packages']]
graph={'packages':packages,'nodes':metadata['resolve']['nodes'],'root':metadata['resolve']['root'],'workspace_members':metadata['workspace_members']}
# Keep complete resolved nodes/features, without the unused declared-feature and target inventory.
(OUT/'resolved-graph.json').write_text(json.dumps(graph,separators=(',',':'))+'\n')
licences=[]
for p in metadata['packages']:
    root=pathlib.Path(p['manifest_path']).parent;texts={}
    for name in ['LICENSE','LICENSE-MIT','LICENSE-APACHE','LICENSE.txt','LICENSE.md','COPYING']:
        f=root/name
        if f.is_file():texts[name]=sha(f.read_bytes())
    licences.append({'name':p['name'],'version':p['version'],'source':p['source'],'license':p['license'],'license_file':p['license_file'],'local_license_texts':texts})
(OUT/'license-inventory.json').write_text(json.dumps(licences,indent=2)+'\n')
info=json.loads(subprocess.check_output([str(HERE/'.venv/bin/python'),'-c','import json,polars,importlib.metadata as m;print(json.dumps({"version":polars.__version__,"build_info":polars.build_info(),"runtime_wheel":m.distribution("polars-runtime-32").read_text("WHEEL"),"runtime_metadata":m.distribution("polars-runtime-32").read_text("METADATA")}))']))
info['wheels']=[];wheels=HERE/'wheels';wheels.mkdir(exist_ok=True)
for package in ['polars','polars-runtime-32']:
    data=js(f'https://pypi.org/pypi/{package}/1.44.2/json')
    matches=[r for r in data['urls'] if r['filename'].endswith('.whl') and ('py3-none-any' in r['filename'] if package=='polars' else 'cp310-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64' in r['filename'])]
    assert len(matches)==1,matches
    r=matches[0];path=wheels/r['filename']
    if not path.exists():path.write_bytes(fetch(r['url']))
    assert sha(path.read_bytes())==r['digests']['sha256']
    site=pathlib.Path(subprocess.check_output([str(HERE/'.venv/bin/python'),'-c','import sysconfig; print(sysconfig.get_paths()["purelib"])'],text=True).strip())
    matched=0
    with zipfile.ZipFile(path) as archive:
        for member in archive.namelist():
            if member.endswith(('.py','.so')):
                assert sha(archive.read(member))==sha((site/member).read_bytes()),member
                matched+=1
    info['wheels'].append({'filename':r['filename'],'url':r['url'],'sha256':r['digests']['sha256'],'bytes':path.stat().st_size,'installed_code_files_matched':matched})
# Published crate's embedded source identity, versus Python tag's repository identity.
polars=next(p for p in metadata['packages'] if p['name']=='polars')
info['rust_crate_vcs']=json.loads((pathlib.Path(polars['manifest_path']).parent/'.cargo_vcs_info.json').read_text())
ref=js('https://api.github.com/repos/pola-rs/polars/git/ref/tags/py-1.44.2');obj=ref['object']
if obj['type']=='tag':obj=js(obj['url'])['object']
info['python_tag_commit']=obj['sha']
for name,rev in [('python',obj['sha']),('rust',info['rust_crate_vcs']['git']['sha1'])]:
    data=fetch(f'https://raw.githubusercontent.com/pola-rs/polars/{rev}/Cargo.toml');(OUT/f'{name}-workspace-Cargo.toml.txt').write_bytes(data)
    info[name+'_workspace_sha256']=sha(data)
info['classification']='different upstream revisions; installed wheel build_info supplies version only; boundary-only matched-engine attribution not established'
(OUT/'provenance.json').write_text(json.dumps(info,indent=2)+'\n');print(info['classification'])
