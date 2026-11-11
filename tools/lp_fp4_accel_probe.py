"""Versioned full-trajectory development checks; not the formal performance cohort."""
import argparse
from pathlib import Path
import time
from lp_fp4_accel_common import ROOT,put,ref,require
from lp_fp4_accel_model import FAMILIES,model
from lp_fp4_accel_run import Service,BINARY,compact


def probe(image,out,audit_max=200,grid=False):
    lanes=('gridnative','gridfp4x2','gridfp4x4') if grid else ('native','fp4x2','fp4x4')
    out=Path(out);out.mkdir(parents=True,exist_ok=False);rows=[];setups=[]
    put(out/'manifest.json',dict(kind='development-trajectory-check',image=ref(image),binary=ref(BINARY),
        source=ref(ROOT/'tools/lp_fp4_accel_probe.py'),families=FAMILIES,lanes=lanes,
        tiers=['certified-1e-7','certified-1e-9'],max_updates=10000,audit_max=audit_max,repetitions=1))
    for family in FAMILIES:
        doc,_=model(family);path=out/(family+'.json');compact(path,doc)
        start=time.monotonic_ns();s=Service(image,path,out/(family+'.stderr'))
        try:
            for lane in lanes:s.call('prepare',lane=lane)
            setups.append(dict(family=family,startup_ns=time.monotonic_ns()-start))
            for tier in ('certified-1e-7','certified-1e-9'):
                for lane in lanes:
                    dest=out/f'{family}-{lane}-{tier}.json'
                    r,elapsed=s.solve_to_file(dest,lane=lane,tier=tier,max_updates=10000,audit_max=audit_max)
                    require(sum(r['costs_ns'].values())==r['solve_ns'],'phase costs do not sum')
                    require(sum(r['attempted'].values())==r['physical'],'physical accounting differs')
                    row=dict(family=family,lane=lane,tier=tier,status=r['status'],certified=r['certified'],physical=r['physical'],
                        gpu_us=r['gpu_us'],complete_ns=elapsed,solve_ns=r['solve_ns'],recovery=[e for e in r['events'] if e['kind']!='window'],result=ref(dest))
                    rows.append(row);print({k:row[k] for k in ('family','lane','tier','status','physical','gpu_us','complete_ns')},flush=True)
        finally:s.close()
    put(out/'result.json',dict(status='complete',rows=rows,setups=setups,formal_performance_evidence=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--image',required=True);p.add_argument('--output',required=True);p.add_argument('--audit-max',type=int,default=200);p.add_argument('--grid',action='store_true');a=p.parse_args()
    probe(Path(a.image),Path(a.output),a.audit_max,a.grid)
