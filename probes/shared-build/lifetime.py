"""The retained-output consumer in the shared directory: what its executable needs, what a later
build in the same directory does to it, and what deleting the directory does."""
from common import *
rows = {}
shutil.rmtree(SHARED, ignore_errors=True); SHARED.mkdir(parents=True)


def build(case, assembly):
    work = T / 'builds' / case
    shutil.copytree(T / 'assemblies' / assembly, work)
    p = run(['cargo', 'build', '--locked', '--offline', '--release', '--target-dir', work / 'target', '--config', f'build.build-dir="{SHARED}"'], cwd=work)
    exe = [e for e in (work / 'target/release').iterdir() if e.is_file() and e.name.startswith('rnx-') and not e.suffix][0]
    return work, exe, len(compiling(p.stderr.decode(errors='replace'))), p.seconds


w1, exe1, n1, t1 = build('l1-retained-disc', 'retained-disc')
b1 = behaviour(exe1, w1)
assert b1['retained'] == 'Ok("cache-owned retained value")', b1
rows['l1'] = {'entries': n1, 'seconds': t1, **b1, 'embeds_shared_path': str(SHARED).encode() in exe1.read_bytes()}
# Another build in the same directory: the first consumer keeps working.
w2, exe2, n2, t2 = build('l2-retained-plain-disc', 'retained-plain-disc')
rows['l2'] = {'entries': n2, 'seconds': t2, **behaviour(exe2, w2)}
rows['l1_after_l2'] = behaviour(exe1, w1)
# A rebuilt native (changed source) leaves a new OUT_DIR beside the old; the old consumer still reads its own.
native = T / 'natives' / 'probe'
(native / 'src/lib.rs').write_text((native / 'src/lib.rs').read_text().replace('"retained()"', '"retained() v2"'))
run(['git', '-C', native, '-c', 'user.name=probe', '-c', 'user.email=probe@example', '-c', 'commit.gpgsign=false', 'commit', '-qam', 'v2'])
w3, exe3, n3, t3 = build('l3-retained-disc-native-changed', 'retained-disc')
rows['l3'] = {'entries': n3, 'seconds': t3, **behaviour(exe3, w3)}
rows['l1_after_l3'] = behaviour(exe1, w1)
# A changed build script re-runs into the same OUT_DIR: the old consumer now reads the new content.
(native / 'build.rs').write_text((native / 'build.rs').read_text().replace('cache-owned retained value', 'REWRITTEN by a later build'))
run(['git', '-C', native, '-c', 'user.name=probe', '-c', 'user.email=probe@example', '-c', 'commit.gpgsign=false', 'commit', '-qam', 'v3 build script'])
w4, exe4, n4, t4 = build('l4-retained-disc-build-script-changed', 'retained-disc')
rows['l4'] = {'entries': n4, 'seconds': t4, **behaviour(exe4, w4)}
rows['l1_after_l4'] = behaviour(exe1, w1)
assert rows['l4']['retained'] == 'Ok("REWRITTEN by a later build")' and rows['l1_after_l4']['retained'] == 'Ok("REWRITTEN by a later build")', rows
# Removal: the consumers' retained file is gone.
shutil.rmtree(SHARED)
def survives(exe, cwd):
    w = Worker(exe, cwd)
    try:
        r = w.op('execute', 'probe::retained()')
        text = r['text_plain'] or ''
        return text.startswith('Ok('), (r['failure'] or text)[:200]
    finally:
        w.close()
rows['l1_after_removal'] = survives(exe1, w1)
rows['l3_after_removal'] = survives(exe3, w3)
assert rows['l1_after_removal'][0] is False and rows['l3_after_removal'][0] is False, rows
save('lifetime.json', rows)
print(json.dumps(rows, indent=1), flush=True)
