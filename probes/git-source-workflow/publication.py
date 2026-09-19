from common import *
import shutil,signal
S=T/'tiny-source-clean';rev=git(S,'rev-parse','HEAD').stdout.decode().strip();rows=[]
for point in ['before-build','after-build','before-ready','ready-written','after-ready','before-attach']:
 p=project('publication-final-'+point,S.as_uri(),rev);e=ENV|{'RNX_PROJECT_CACHE':str(T/('publication-final-cache-'+point))}
 run([TOOL,'lock','--offline','--manifest',p/'rnx.toml'],env=e);lock=json.loads((p/'rnx.lock').read_text());key=run([T/'b3'],data=lock['assembly']['identity'].encode()).stdout.decode().strip();entry=Path(e['RNX_PROJECT_CACHE'])/'entries'/key
 r=run([TOOL,'build','--offline','--manifest',p/'rnx.toml'],env=e|{'RNX_CACHE_FAIL':point},ok=False);assert r.returncode and not (p/'.rnx/receipt.json').exists()
 assert (entry/'ready.json').exists()==(point in ['after-ready','before-attach'])
 run([TOOL,'build','--offline','--manifest',p/'rnx.toml'],env=e);assert json.loads((entry/'ready.json').read_text())['format']==3
 rows.append({'case':point,'refused':True,'retry_passed':True})
# An edit made by a successful Cargo build must refuse readiness and receipt.
p=project('publication-final-edit',S.as_uri(),rev);e=ENV|{'RNX_PROJECT_CACHE':str(T/'publication-final-cache-edit')};run([TOOL,'lock','--offline','--manifest',p/'rnx.toml'],env=e)
lock=json.loads((p/'rnx.lock').read_text());root=Path(lock['git'][0]['checkout']);f=root/'src/lib.rs';old=f.read_bytes();marker=T/'publication-final-paused'
child=subprocess.Popen([str(TOOL),'build','--offline','--manifest',str(p/'rnx.toml')],env=e|{'RNX_CACHE_PAUSE':'after-build','RNX_CACHE_MARKER':str(marker)},stdout=subprocess.PIPE,stderr=subprocess.PIPE)
try:
 end=time.monotonic()+30
 while not marker.exists():
  assert child.poll() is None;assert time.monotonic()<end;time.sleep(.01)
 f.write_bytes(old+b'// changed during compilation\n');marker.unlink();out,err=child.communicate(timeout=30);(O/'post-build-edit.stderr').write_bytes(err);assert child.returncode and b'Git' in err
 assert not (p/'.rnx/receipt.json').exists() and not list(Path(e['RNX_PROJECT_CACHE']).glob('entries/*/ready.json'))
 rows.append({'case':'after-build-source-edit','refused':True,'reason':err.decode()})
finally:
 f.write_bytes(old)
 if child.poll() is None:child.kill();child.wait()
run([TOOL,'build','--offline','--manifest',p/'rnx.toml'],env=e)
save('publication.json',rows);print(len(rows),'real publication cases pass',flush=True)
