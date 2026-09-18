"""Inclusive clocks and disjoint derived children; no cache policy or speedup claim."""
from pathlib import Path
import json,statistics as st,collections,hashlib,subprocess as sp,ast
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parent/'rnx';O=B/'results/native-inventory-0065';W=H/'target'
meta=json.loads((O/'measurement.json').read_text());samples=[json.loads(s) for s in (O/'samples.jsonl').read_text().splitlines()];assert len(samples)==meta['total'];groups=collections.defaultdict(list)
for r in samples:groups[(r['kind'],r['layout'],r['count'],r['route'],r['repeat'])].append(r)
summary=[];detail=[]
for key,rs in sorted(groups.items()):
 assert len(rs)==meta['samples_per_cell']
 row=dict(zip(['kind','layout','count','route','repeat'],key));row['median_ms']=st.median(r['wall_ns']/1e6 for r in rs);row['min_ms']=min(r['wall_ns']/1e6 for r in rs);row['max_ms']=max(r['wall_ns']/1e6 for r in rs)
 if 'inventory_ms' in rs[0]:row['inventory_ms']=st.median(r['inventory_ms'] for r in rs)
 summary.append(row)
 if 'profile' in rs[0]:
  keys=sorted(rs[0]['profile']['ns']);assert all(sorted(r['profile']['ns'])==keys for r in rs)
  med={k:st.median(r['profile']['ns'][k]/1e6 for r in rs) for k in keys}
  calls=rs[0]['profile']['calls'];assert all(r['profile']['calls']==calls for r in rs)
  for root in sorted({k.split('|')[1] for k in keys if k.startswith('tree|')}):
   vals={k.split('|')[2]:v for k,v in med.items() if k.startswith('tree|'+root+'|')}
   # Subtract within each observation before taking a median.
   for label,terms in [('tree_other',['path_metadata','open_metadata','read','digest']),('native_other',['git_submodule','git_untracked','git_tracked','tree_total'])]:
    base='tree_total' if label=='tree_other' else 'total'
    values=[(r['profile']['ns']['tree|'+root+'|'+base]-sum(r['profile']['ns']['tree|'+root+'|'+x] for x in terms))/1e6 for r in rs];assert min(values)>=0;vals[label]=st.median(values)
   detail.append(dict(kind=key[0],layout=key[1],count=key[2],repeat=key[4],root=root,ms=vals,audit_ms=med.get('audit|'+root,0),audit_candidates=calls.get('audit|'+root,0)))
  row['inventory_profile_ms']=med['inventory_total'];row['audit_total_ms']=med['audit_total'];row['shared_audit_ms']=med.get('audit|shared',0);row['shared_audit_candidates']=calls.get('audit|shared',0)
(O/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(O/'trees.json').write_text(json.dumps(detail,indent=2)+'\n')
def get(kind,layout,count,route,rep):return next(x for x in summary if (x['kind'],x['layout'],x['count'],x['route'],x['repeat'])==(kind,layout,count,route,rep))
effects=[];slopes=[]
for rep in range(2):
 fixed=get('fixed-direct','all',-1,'direct',rep)['median_ms']
 totals=[]
 for count in range(4):
  product=get('product','shallow',count,'stock',rep)['median_ms'];direct=get('product','shallow',count,'direct',rep)['median_ms'];total=product-direct;totals.append(total)
  shape={layout:get('fixed',layout,count,'stock',rep)['inventory_ms'] for layout in ['shallow','deep','long']}
  effects.append(dict(repeat=rep,count=count,product_over_direct_ms=total,fixed_over_direct_ms=get('fixed','shallow',count,'stock',rep)['median_ms']-fixed,inventory_ms=shape,deep_minus_shallow_ms=shape['deep']-shape['shallow'],long_minus_shallow_ms=shape['long']-shape['shallow'],deep_minus_long_ms=shape['deep']-shape['long'],product_clock_delta_ms=get('product','shallow',count,'profile',rep)['median_ms']-product,fixed_clock_delta_ms=get('fixed','shallow',count,'profile',rep)['median_ms']-get('fixed','shallow',count,'stock',rep)['median_ms']))
 slope=st.linear_regression(range(4),totals)
 slopes.append(dict(repeat=rep,intercept_ms=slope.intercept,slope_ms_per_adapter=slope.slope,marginal_ms=[totals[i]-totals[i-1] for i in range(1,4)]))
 print('repeat',rep,'product over direct',totals,'descriptive slope',slope.slope,flush=True)
(O/'slopes.json').write_text(json.dumps(slopes,indent=2)+'\n')
(O/'effects.json').write_text(json.dumps(effects,indent=2)+'\n')
for p in H.glob('*.py'):ast.parse(p.read_text())
assert not sp.check_output(['git','-C',R,'status','--porcelain','--untracked-files=normal'])
assert sp.check_output(['git','-C',R,'rev-parse','HEAD'],text=True).strip()==json.loads((O/'provenance.json').read_text())['base']
print('PASS all observations, clock partitions and unchanged rnx')
