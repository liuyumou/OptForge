"""Matched host preparation measurements; exact prior sources remain untouched."""
import time
import numpy as np
from lp_fp4_fast_common import BASE, put, ref
import lp_fp4_fast_prepare as fast
import lp_fp4_gpu_oracle as oracle


def main():
    rows=[]
    for rep in range(3):
        for f,k in oracle.LANES:
            oracle.encode.cache_clear()
            begin=time.monotonic_ns();old=oracle.request('dense-2048',f,k);old_ns=time.monotonic_ns()-begin
            begin=time.monotonic_ns();new=fast.request(64,f,k,'legacy' if f==64 else 'hardware');new_ns=time.monotonic_ns()-begin
            expected={**old,'backend':new['backend'],'repetitions':1}
            if new!=expected:raise ValueError('preparation differs')
            rows.append(dict(repetition=rep,format=f,components=k,rational_ns=old_ns,vectorized_ns=new_ns,exact_match=True))
            print(f,k,old_ns,new_ns,flush=True)
    put(BASE/'host-preparation.json',dict(rows=rows,numpy=np.__version__,source=ref(fast.__file__),reference=ref(oracle.__file__)))

if __name__=='__main__':main()
