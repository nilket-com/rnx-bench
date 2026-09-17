"""Recheck cached wheel/installed-code identity without another network fetch."""
import hashlib,json,pathlib,subprocess,zipfile
HERE=pathlib.Path(__file__).resolve().parent;BENCH=HERE.parents[1];OUT=BENCH/'results/polars-cost-0058';PY=HERE/'target/python/bin/python'
source=json.loads((BENCH/'results/polars-boundary-0058/provenance.json').read_text())
site=pathlib.Path(subprocess.check_output([str(PY),'-c','import sysconfig; print(sysconfig.get_paths()["purelib"])'],text=True).strip())
verified=[]
for item in source['wheels']:
 path=HERE.parent/'polars-boundary/wheels'/item['filename'];assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
 count=0
 with zipfile.ZipFile(path) as z:
  for name in z.namelist():
   if name.endswith(('.py','.so')):
    assert hashlib.sha256(z.read(name)).digest()==hashlib.sha256((site/name).read_bytes()).digest();count+=1
 verified.append({'filename':item['filename'],'sha256':item['sha256'],'installed_code_files_verified':count})
result={'wheels':verified,'python':subprocess.check_output([str(PY),'-VV'],text=True),'polars':json.loads(subprocess.check_output([str(PY),'-c','import polars,json; print(json.dumps({"version":polars.__version__,"build_info":polars.build_info()}))'],text=True)), 'rust_crate_vcs':source['rust_crate_vcs'],'python_tag_commit':source['python_tag_commit'],'classification':source['classification'],'bytecode_files_after_warmup':len(list(site.rglob('*.pyc')))}
assert result['bytecode_files_after_warmup']>0
(OUT/'provenance.json').write_text(json.dumps(result,indent=2)+'\n')
print('exact cached wheels and installed code verified; different engine revisions remain explicit')
# Preserve known build/allocator context without guessing the wheel's internals.
import os
context=json.loads(subprocess.check_output([str(PY),'-c','import sysconfig,json,os;print(json.dumps({"config":{k:sysconfig.get_config_var(k) for k in ["Py_GIL_DISABLED","WITH_PYMALLOC","WITH_MIMALLOC","CC","CFLAGS"]},"PYTHONMALLOC":os.getenv("PYTHONMALLOC","default")}))'],text=True))
context.update(site_packages_bytes=sum(p.stat().st_size for p in site.rglob('*') if p.is_file()),site_packages_pyc_bytes=sum(p.stat().st_size for p in site.rglob('*.pyc')),wheel_allocator='stock pinned wheel; allocator implementation and complete wheel compiler flags not established by build_info, so no matching-allocator claim',rnx_allocator='count-allocations feature: counting wrapper around Rust System; no replacement allocator in the Polars adapter',cold_build_overrides={k:os.getenv(k) for k in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','CARGO_BUILD_RUSTC_WRAPPER','CARGO_TARGET_DIR']})
(OUT/'allocation-build-context.json').write_text(json.dumps(context,indent=2)+'\n')
