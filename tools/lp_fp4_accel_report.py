"""Replay every unique formal endpoint with the original serial certificate and summarize costs."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import tempfile
import numpy as np
from lp_fp4_accel_common import ROOT,put,ref,load,require
from lp_fp4_accel_run import BINARY,compact
from lp_fp4_accel_study import LANES,TIERS
from lp_fp4_accel_model import FAMILIES


def summarize(directory,output):
    directory=Path(directory);output=Path(output);m=load(directory/'manifest.json');r=load(directory/'result.json');rows=r['rows']
    require(len(rows)==len(m['cells']) and {v['id'] for v in rows}=={v['id'] for v in m['cells']},'incomplete formal coverage')
    endpoints={};certified=0
    for row in rows:
        require(ref(ROOT/row['result']['path'])==row['result'],'changed result')
        result=load(ROOT/row['result']['path'])
        require(row['complete_ns']>=row['solve_ns'],'complete cost boundary')
        certified+=int(row['certified'])
        for e,c in [(result['endpoint'],result['certificate'])]+[(a['endpoint'],a['certificate']) for a in result['audits']]:
            key=hashlib.sha256(json.dumps([e,row['tier']],sort_keys=True,separators=(',',':')).encode()).hexdigest()
            record=dict(family=row['family'],tier=row['tier'],endpoint=e,certificate=c)
            if key in endpoints:require(endpoints[key]==record,'nondeterministic original receipt')
            else:endpoints[key]=record
    with tempfile.TemporaryDirectory() as tmp:
        for i,(key,record) in enumerate(endpoints.items()):
            path=Path(tmp);ep=path/f'{i}.endpoint.json';dest=path/f'{i}.certificate.json';compact(ep,record['endpoint'])
            subprocess.run([str(BINARY),'check-serial',str(ROOT/m['models'][record['family']]['path']),str(ep),record['tier'],str(dest)],check=True,capture_output=True,timeout=30)
            require(load(dest)==record['certificate'],'serial authority differs: '+key)
    medians=[];decisions=[];rng=np.random.default_rng(310063)
    for lifecycle in ('cold','prepared'):
        for tier in TIERS:
            groups={}
            for family in FAMILIES:
                for lane in LANES:
                    cell=sorted([v for v in rows if v['lifecycle']==lifecycle and v['tier']==tier and v['family']==family and v['lane']==lane],key=lambda x:x['repetition'])
                    require(len(cell)==5,'missing repetitions');groups[family,lane]=cell
                    medians.append(dict(lifecycle=lifecycle,tier=tier,family=family,lane=lane,certified=sum(v['certified'] for v in cell),
                        complete_ms=statistics.median(v['complete_ns'] for v in cell)/1e6,gpu_ms=statistics.median(v['gpu_us'] for v in cell)/1e3,
                        physical=statistics.median(v['physical'] for v in cell),recovery=sum(len(v['recovery']) for v in cell),
                        phase_ms={k:statistics.median(v['costs_ns'].get(k,0) for v in cell)/1e6 for k in {k for v in cell for k in v['costs_ns']}}))
            families=[f for f in FAMILIES if all(v['certified'] for v in groups[f,'nativefast'])]
            for lane in LANES:
                losses=[f for f in FAMILIES if sum(v['certified'] for v in groups[f,lane])<sum(v['certified'] for v in groups[f,'nativefast'])]
                ratios=[];regressions=[];boot=[]
                for f in families:
                    a=np.array([v['complete_ns'] for v in groups[f,'nativefast']],dtype=float);b=np.array([v['complete_ns'] for v in groups[f,lane]],dtype=float)
                    ratio=float(np.median(a)/np.median(b));ratios.append(ratio)
                    if ratio<1:regressions.append(f)
                    index=rng.integers(0,5,size=(2000,5));boot.append(np.median(a[index],axis=1)/np.median(b[index],axis=1))
                gm=float(np.exp(np.log(ratios).mean()));distribution=np.exp(np.log(boot).mean(axis=0));ci=list(map(float,np.quantile(distribution,[.025,.975])))
                decisions.append(dict(lifecycle=lifecycle,tier=tier,lane=lane,reference='nativefast',certified_families=families,geomean=gm,bootstrap95=ci,
                    model_regressions=regressions,coverage_losses=losses,retention_pass=lifecycle=='cold' and gm>=1.10 and not regressions and not losses))
    bundle=dict(manifest=m,models={f:load(ROOT/v['path']) for f,v in m['models'].items()},endpoints=endpoints)
    archive=output.with_name(output.stem+'-endpoints.json.gz');archive.write_bytes(gzip.compress(json.dumps(bundle,separators=(',',':'),allow_nan=False).encode(),mtime=0))
    put(output,dict(status='complete',manifest=ref(directory/'manifest.json'),raw_results=ref(directory/'result.json'),cells=len(rows),certified=certified,
        unique_serial_replays=len(endpoints),endpoint_archive=ref(archive),rows=rows,setups=r['setups'],medians=medians,decisions=decisions,
        uncertainty='2000 paired within-model repetition bootstrap resamples; five trials/model, constructed development models, not a held-out generalization claim'))
    print(dict(cells=len(rows),certified=certified,unique_serial_replays=len(endpoints),decisions=decisions),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',required=True);p.add_argument('--output',required=True);a=p.parse_args();summarize(Path(a.study),Path(a.output))
