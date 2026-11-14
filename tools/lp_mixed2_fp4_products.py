"""Explicit fixed-operand product/guard diagnosis; never a solver adoption test."""
import argparse
from pathlib import Path
import random
import time
from lp_mixed2_fp4_common import ROOT,BASE,BINARY,load,put,ref,require
from lp_mixed2_fp4_transport import Service


def run(out,image,admission,sanitizer_version):
    out=Path(out);out.mkdir(exist_ok=False);image=Path(image);admission=Path(admission)
    require(load(admission/'manifest.json')['image']==ref(image) and load(admission/'manifest.json')['binary']==ref(BINARY),'device binding')
    for name in ('memcheck','racecheck','initcheck','synccheck'):
        p=BASE/(name+'-'+sanitizer_version);require(load(p/'result.json')['status']=='passed' and load(p/'manifest.json')['image']==ref(image),'sanitizer binding')
    models=load(BASE/'models/manifest.json');families=('dense-generic-128','dense-generic-256','dense-generic-512','dense-generic-1024','dense-generic-2048')
    rng=random.Random(380073);put(out/'manifest.json',dict(binary=ref(BINARY),image=ref(image),models=ref(BASE/'models/manifest.json'),seed=380073,blocks=3,count=128,families=families,admission=ref(admission/'result.json')))
    rows=[]
    for block in range(3):
        fs=list(families);rng.shuffle(fs)
        for family in fs:
            s=Service(image,ROOT/models['models'][family]['path'],out/f'b{block}-{family}.log')
            try:
                lanes=['native','fp4x2','fp4x4'];rng.shuffle(lanes)
                for lane in lanes:
                    start=time.monotonic_ns();s.call('debug_reset',lane=lane);prepare=time.monotonic_ns()-start
                    raw=s.call('debug_export')['raw'];cases=[(tr,guarded) for tr in (False,True) for guarded in (False,True)];rng.shuffle(cases)
                    for tr,guarded in cases:
                        op=('debug_bench_' if guarded else 'debug_unguarded_')+('transpose' if tr else 'forward')
                        start=time.monotonic_ns();result=s.call(op,count=128);elapsed=time.monotonic_ns()-start
                        row=dict(block=block,family=family,lane=lane,transpose=tr,guarded=guarded,prepare_ns=prepare,roundtrip_ns=elapsed,result=result,raw=raw)
                        dest=out/f'b{block}-{family}-{lane}-{int(tr)}-{int(guarded)}.json';put(dest,row)
                        rows.append(dict(**{k:v for k,v in row.items() if k not in ('result','raw')},gpu_per_product_us=result['gpu_us']/128,vector_prepare_ns=result['preparation_ns'],record=ref(dest)))
                    s.call('debug_finish')
            finally:s.close()
    put(out/'result.json',dict(status='complete',rows=rows));print(dict(status='complete',cells=len(rows)),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('--image',required=True);p.add_argument('--admission',required=True);p.add_argument('--sanitizer-version',required=True);a=p.parse_args();run(a.out,a.image,a.admission,a.sanitizer_version)
