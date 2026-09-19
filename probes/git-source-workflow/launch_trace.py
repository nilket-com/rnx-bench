from common import *
setup=json.loads((O/'real-setup.json').read_text());exe=Path(setup['exe']);row=json.loads((O/'real-journeys.json').read_text())[1];p=Path(row['manifest']);lock=json.loads((p.parent/'rnx.lock').read_text());roots={g['checkout'] for g in lock['git']};trace=O/'real-everyday.trace'
r=run(['strace','-f','-qq','-o',trace,'-e','trace=execve,openat,connect',exe,'project','eval','--manifest',p,'--','polars::lit(42)']);text=trace.read_text()
assert not any('execve(' in line and any('/'+name+'"' in line for name in ['git','cargo','rustc']) for line in text.splitlines())
assert not any('openat(' in line and any(root+'/' in line for root in roots) for line in text.splitlines())
assert 'AF_INET' not in text
save('real-everyday-trace.json',{'roots':sorted(roots),'git_cargo_rustc_execs':0,'native_source_opens':0,'internet_connects':0,'stdout':r.stdout.decode(),'trace_sha256':sha(trace.read_bytes())})
# Missing checkout and a symlink replacement refuse, while a replacement at the
# same canonical directory with modified content is the documented default miss.
root=Path(next(iter(roots)));moved=root.with_name(root.name+'-temporarily-moved');root.rename(moved)
try:
 r=run([exe,'project','eval','--manifest',p,'--','42'],ok=False);assert r.returncode
 root.symlink_to(moved,target_is_directory=True)
 r2=run([exe,'project','eval','--manifest',p,'--','42'],ok=False);assert r2.returncode
finally:
 if root.is_symlink():root.unlink()
 moved.rename(root)
save('checkout-structure.json',{'missing':r.returncode,'symlink':r2.returncode,'reasons':[r.stderr.decode(),r2.stderr.decode()]})
print('Real launch trace and structural checkout refusals pass',flush=True)
