import sys,statistics
from common import *
sys.path.insert(0,str(ROOT/'probes/jupyter-supervision'))
import probe
probe.OUT=OUT
records=[]
for run in range(20):
    start=time.perf_counter();k=probe.Kernel();ready=time.perf_counter()-start
    try:
        start=time.perf_counter();r,m=k.execute('1 + 1');first=time.perf_counter()-start;assert probe.result(m)=='2'
        warm=[]
        for _ in range(30):
            start=time.perf_counter();r,m=k.execute('1 + 1');warm.append(time.perf_counter()-start);assert probe.result(m)=='2'
        records.append(dict(ready=ready,first=first,warm=warm))
    finally:k.close()
(OUT/'latency-raw.json').write_text(json.dumps(records,indent=2)+'\n')
summary={name:dict(median=statistics.median(values),minimum=min(values),maximum=max(values)) for name,values in [('ready',[r['ready'] for r in records]),('first',[r['first'] for r in records]),('warm',[t for r in records for t in r['warm']])]}
(OUT/'latency.json').write_text(json.dumps(summary,indent=2)+'\n');log('client_observed_latency_seconds',**summary)
