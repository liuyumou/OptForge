"""All-cell exact evidence verification, paired uncertainty, and complete-cost attribution."""
import argparse
import json
from pathlib import Path
import statistics
import numpy as np
from lp_fp4_checker_common import ROOT,BASE,load,put,ref,require
from lp_fp4_checker_study import matches,LANES,TIERS


def summarize():
    directory=BASE/'study-v1';m=load(directory/'manifest.json');result=load(directory/'result.json')
    require(result['status']=='complete' and len(result['rows'])==len(m['cells'])==960,'incomplete comparison')
    require({r['id'] for r in result['rows']}=={c['id'] for c in m['cells']},'coverage mismatch')
    rows=result['rows'];bindings=[]
    for r in rows:
        require(ref(ROOT/r['result']['path'])==r['result'],'changed observed result')
        require(ref(ROOT/r['original_result']['path'])==r['original_result'],'changed original evidence')
        observed=load(ROOT/r['result']['path']);old=load(ROOT/r['original_result']['path'])
        matches(observed,old,m['binaries'][r['checker']])
        bindings.append(dict(id=r['id'],observed=r['result'],original=r['original_result'],audits=len(observed['audits'])))
    families=list(m['models']);medians=[];decisions=[];rng=np.random.default_rng(320064)
    for lifecycle in ('cold','prepared'):
        for tier in TIERS:
            groups={}
            for family in families:
                for checker in ('original','optimized'):
                    for lane in LANES:
                        group=sorted([r for r in rows if r['lifecycle']==lifecycle and r['tier']==tier and r['family']==family and r['checker']==checker and r['lane']==lane],key=lambda r:r['repetition'])
                        require(len(group)==5,'missing repetitions');groups[family,checker,lane]=group
                        median=dict(lifecycle=lifecycle,tier=tier,family=family,checker=checker,lane=lane,
                            certified=sum(r['certified'] for r in group),complete_ms=statistics.median(r['complete_ns'] for r in group)/1e6,
                            gpu_ms=statistics.median(r['gpu_us'] for r in group)/1e3,physical=statistics.median(r['physical'] for r in group),
                            solve_ms=statistics.median(r['solve_ns'] for r in group)/1e6,setup_ms=statistics.median(r['setup_ns'] for r in group)/1e6,
                            phase_ms={k:statistics.median(r['costs_ns'].get(k,0) for r in group)/1e6 for k in sorted({k for r in group for k in r['costs_ns']})})
                        if median['physical']:median['gpu_us_per_update']=median['gpu_ms']*1e3/median['physical']
                        medians.append(median)
            for comparison,control,candidate in [
                ('checker-native',('original','nativefast'),('optimized','nativefast')),
                ('checker-fp4',('original','gridfp4x2'),('optimized','gridfp4x2')),
                ('fp4-original-checker',('original','nativefast'),('original','gridfp4x2')),
                ('fp4-optimized-checker',('optimized','nativefast'),('optimized','gridfp4x2'))]:
                certified=[f for f in families if all(r['certified'] for r in groups[f,*control])]
                ratios=[];bootstrap=[];regressions=[]
                losses=[f for f in families if sum(r['certified'] for r in groups[f,*candidate])<sum(r['certified'] for r in groups[f,*control])]
                for f in certified:
                    a=np.array([r['complete_ns'] for r in groups[f,*control]],float);b=np.array([r['complete_ns'] for r in groups[f,*candidate]],float)
                    ratio=float(np.median(a)/np.median(b));ratios.append(ratio)
                    if ratio<1:regressions.append(f)
                    index=rng.integers(0,5,(2000,5));bootstrap.append(np.median(a[index],axis=1)/np.median(b[index],axis=1))
                gm=float(np.exp(np.log(ratios).mean()));interval=list(map(float,np.quantile(np.exp(np.log(bootstrap).mean(axis=0)),[.025,.975])))
                decisions.append(dict(lifecycle=lifecycle,tier=tier,comparison=comparison,control=control,candidate=candidate,
                    geomean=gm,bootstrap95=interval,model_regressions=regressions,coverage_losses=losses,
                    retention_pass=lifecycle=='cold' and gm>=1.1 and not regressions and not losses))
    profiles=load(BASE/'profile-final/result.json');cpu=[]
    for r in profiles['rows']:
        raw=load(ROOT/r['profile']['path']);require(ref(ROOT/r['profile']['path'])==r['profile'],'changed CPU profile')
        cpu.append(dict(**r,samples=[x for x in raw['rows'] if x['baseline']==r['baseline']]))
    data=dict(status='complete',manifest=m,manifest_binding=ref(directory/'manifest.json'),cells=len(rows),
        certified=sum(r['certified'] for r in rows),rows=rows,setups=result['setups'],medians=medians,decisions=decisions,
        exact_equivalence=bindings,cpu_profiles=cpu,retained_unique_serial_receipts=102,
        uncertainty='2000 within-model paired bootstrap resamples, five trials; constructed development models up to 512 rows/columns, not production generalization')
    put(ROOT/'docs/benchmarks/data/fp4-checker-result-v1.json',data)
    for d in decisions:print(d,flush=True)
    for r in medians:
        if r['family']=='dense-generic-512' and r['tier']=='certified-1e-9':print(r,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.parse_args();summarize()
