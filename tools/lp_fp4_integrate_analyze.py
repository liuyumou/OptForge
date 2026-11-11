"""Complete same-tier coverage and timing summaries, retaining every cell."""
import argparse,math,statistics
from pathlib import Path
import numpy as np
from lp_fp4_integrate_common import load,put,ref,require
from lp_fp4_integrate_model import FAMILIES,LANES
from lp_fp4_integrate_study import TIERS

def analyze(diagnostic,performance,output):
 d=load(diagnostic);p=load(performance);require(d['complete'] and p['complete'],'partial grid')
 require(len(d['rows'])==96 and len(p['rows'])==576,'grid coverage')
 diag=[];comparisons=[];rng=np.random.default_rng(20261111)
 for tier in TIERS:
  for lane in LANES:
   rows=[r for r in d['rows'] if r['tier']==tier and r['lane']==list(lane)]
   diag.append(dict(tier=tier,lane=lane,certified=sum(r['certified'] for r in rows),total=len(rows),physical=sum(r['physical'] for r in rows),fp4=sum(r['fp4'] for r in rows),refused=[r['family'] for r in rows if not r['certified']]))
 for tier in TIERS:
  for lifecycle in ('cold','prepared'):
   for lane in LANES[1:]:
    models=[];boot=[];missing=[];native_families=[]
    for family in FAMILIES:
     select=lambda l:sorted([r for r in p['rows'] if r['family']==family and r['tier']==tier and r['lifecycle']==lifecycle and r['lane']==list(l)],key=lambda r:r['rep'])
     native,candidate=select((64,1)),select(lane);require(len(native)==len(candidate)==3,'missing timing repetition')
     ok=all(r['certified'] for r in native);candidate_ok=all(r['certified'] for r in candidate)
     if ok:native_families.append(family)
     if ok and not candidate_ok:missing.append(family)
     record=dict(family=family,native_certified=sum(r['certified'] for r in native),candidate_certified=sum(r['certified'] for r in candidate),native_ns=[r['outer_ns'] for r in native],candidate_ns=[r['outer_ns'] for r in candidate],native_physical=[r['physical'] for r in native],candidate_physical=[r['physical'] for r in candidate])
     if ok and candidate_ok:
      a=np.array(record['native_ns'],dtype=float);b=np.array(record['candidate_ns'],dtype=float);ratio=float(np.median(a)/np.median(b));idx=rng.integers(0,3,size=(2000,3));bootstrap=np.median(a[idx],axis=1)/np.median(b[idx],axis=1);boot.append(np.log(bootstrap))
      record.update(ratio=ratio,bootstrap_95=np.quantile(bootstrap,[.025,.975]).tolist(),gpu_ratio=statistics.median(r['gpu_us'] for r in native)/statistics.median(r['gpu_us'] for r in candidate))
     models.append(record)
    good=[r for r in models if 'ratio' in r];gm=math.exp(statistics.mean(math.log(r['ratio']) for r in good)) if good else None
    ci=np.quantile(np.exp(np.mean(boot,axis=0)),[.025,.975]).tolist() if boot else None
    regressions=[r['family'] for r in good if r['ratio']<1]
    comparisons.append(dict(tier=tier,lifecycle=lifecycle,lane=lane,models=models,certified_native_families=native_families,coverage_loss=missing,regressions=regressions,geomean=gm,bootstrap_95=ci,retention=bool(gm is not None and gm>=1.10 and not regressions and not missing)))
 result=dict(diagnostic=ref(diagnostic),performance=ref(performance),diagnostic_summary=diag,comparisons=comparisons,prepared_startup=p['prepared_startup'],bootstrap=dict(repetitions=2000,seed=20261111,method='paired repetition resampling within each fixed family; 3 repetitions; descriptive timing uncertainty only'),performance_certified=sum(r['certified'] for r in p['rows']),performance_total=576)
 put(output,result)
 for c in comparisons:
  print(c['tier'],c['lifecycle'],c['lane'],'GM',c['geomean'],'CI',c['bootstrap_95'],'regressions',len(c['regressions']),'coverage_loss',c['coverage_loss'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--diagnostic',required=True);p.add_argument('--performance',required=True);p.add_argument('--output',required=True);a=p.parse_args();analyze(Path(a.diagnostic),Path(a.performance),Path(a.output))
