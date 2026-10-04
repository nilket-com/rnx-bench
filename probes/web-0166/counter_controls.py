"""Fail-closed counter parser controls on a retained good perf artifact."""
import importlib.util,json,pathlib,sys
p=pathlib.Path(__file__).with_name('counter_gate.py')
spec=importlib.util.spec_from_file_location('counter_gate',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
raw=pathlib.Path(sys.argv[1]).read_text();m.perf_counts(raw)
rows=[json.loads(l) for l in raw.splitlines() if l.strip()]
mut=[('missing event',rows[:1]),('duplicate event',[rows[0],rows[0]])]
for name,key,value in [('not counted','counter-value','<not counted>'),('nonfinite','counter-value','nan'),('zero','counter-value','0'),('low running','pcnt-running',50),('zero runtime','event-runtime',0),('wrong PMU','event','cpu_atom/instructions/u')]:
 r=json.loads(json.dumps(rows));r[0][key]=value;mut.append((name,r))
for name,r in mut:
 try:m.perf_counts('\n'.join(json.dumps(v) for v in r))
 except (AssertionError,ValueError,KeyError):print(name,'REFUSED')
 else:raise AssertionError(name+' accepted')
print('unmodified PASS; 8 malformed counters REFUSED')
