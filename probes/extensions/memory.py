#!/usr/bin/env python3
import json,os,pathlib,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2];OUT=ROOT/'results/extensions-0051'
sys.path.insert(0,str(ROOT.parent/'rnx/tests'))
from worker_parent import Parent
results={}
with tempfile.TemporaryDirectory() as d:
    env=dict(os.environ,TERM='xterm',RNX_CONFIG=d+'/absent',RNX_HISTORY=d+'/history')
    env.pop('RNX_FIXTURE_MARKER',None);env.pop('RNX_MEMORY_CEILING',None)
    for label,binary in zip(['stock','app'],sys.argv[1:3]):
        def peak(source):
            r=subprocess.run([binary,'eval',source],env=env,capture_output=True,text=True,timeout=15)
            assert r.returncode==0,(source,r.stderr)
            return int(r.stdout)
        baseline=peak('rnx_test::test_reset_allocation_peak(); rnx_test::test_allocation_peak()')
        large=peak('rnx_test::test_reset_allocation_peak(); let s = String::with_capacity(1048576); rnx_test::test_allocation_peak()')
        w=Parent(binary,dict(env,RNX_MEMORY_CEILING='1'))
        try:
            refusal,messages,_=w.execute('42')
            assert refusal['failure']['category']=='over_ceiling' and refusal['input'] is None and len(messages)==1,refusal
        finally:w.close()
        results[label]={'baseline_peak':baseline,'large_peak':large,'increase':large-baseline,'ceiling_refusal':refusal['failure']}
    assert abs(results['app']['increase']-results['stock']['increase']) <= 4096,results
    assert all(abs(r['increase']-1048576) <= 4096 for r in results.values()), results
    for r in results.values():
        failure=r['ceiling_refusal']
        assert failure['diagnostic']==f"tracked live allocation request bytes {failure['live']} are at or above the ceiling of 1; :reset to continue", failure
        assert failure['ceiling']==1 and failure['origin'] is None and not failure['diagnostic_truncated'],failure
results['tolerance_bytes']=4096
(OUT/'memory.json').write_text(json.dumps(results,indent=2)+'\n')
print('allocator inheritance and ceiling gates passed')
