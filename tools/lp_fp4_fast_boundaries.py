"""Supplemental exact-state projection-boundary coverage for the final image."""
import shutil
import numpy as np
from lp_fp4_fast_common import BASE, ROOT, put, ref, require
from lp_fp4_fast_experiment import execute
from lp_fp4_fast_prepare import request, encode_batch
from lp_fp4_gpu_oracle import LANES, reference, observed_error


def main():
    d=BASE/'projection-boundaries-v1';d.mkdir(exist_ok=False)
    binary=BASE/'study-v1/executor';shutil.copyfile(binary,d/'executor');(d/'executor').chmod(0o755)
    image=BASE/'build-v8/fast.cubin';rows=[]
    put(d/'manifest.json',dict(binary=ref(d/'executor'),image=ref(image),driver=ref(ROOT/'tools/lp_fp4_fast_boundaries.py'),purpose='supplemental projection boundary validation; no timing cell rerun'))
    for f,k in LANES:
        for updates in (1,8,32):
            r=request(2,f,k,'legacy',n=29,updates=updates,repetitions=2,arrays=True)
            r['matrix'][:]=0;r['cb'][:]=0
            for b in range(2):
                for i in range(29):
                    r['initial'][b*96+i]=1. if i%2==0 else -1.
                    r['initial'][b*96+64+i]=r['initial'][b*96+i]
                    r['cb'][b*64+i]=(1 if i%4<2 else -1)*2.**-26
            if f!=64:r['matrix_codes'],r['matrix_exponents']=encode_batch(r['matrix'].reshape(2,1024),f,k,arrays=True)
            expected=None
            for backend in ('legacy','native_cached') if f==64 else ('legacy','hardware'):
                r['backend']=backend;name=f'{f}-{k}-{updates}-{backend}'
                row,out=execute(d,name,r,image)
                require(out['status']=='completed','boundary refusal')
                endpoint=[out[x] for x in ('state','codes','exponents','observed_flags')]
                if expected is None:expected=endpoint
                else:require(endpoint==expected,'projection boundary changed endpoint')
                row['observed_error']=observed_error(out['state'],reference(r,updates));rows.append(row)
    put(ROOT/'docs/benchmarks/data/fp4-fast-projection-boundaries-v1.json',dict(status='passed',cases=len(rows),manifest=ref(d/'manifest.json'),rows=rows,certified=False))
    print(len(rows),'projection-boundary cases passed with exact same-lane endpoints.')

if __name__=='__main__':main()
