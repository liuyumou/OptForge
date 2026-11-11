"""Independent exact-oracle checks for optimized host preparation."""
import sys
from pathlib import Path
import unittest
import tempfile
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import lp_fp4_gpu_oracle as oracle
import lp_fp4_fast_prepare as fast


class FastPreparation(unittest.TestCase):
    def compare(self,a,f,k):
        w,e=fast.encode_batch(a,f,k);expected_w=[];expected_e=[]
        for block in a:
            ow,oe,_,_=oracle.encode(tuple(map(float,block)),f,k)
            expected_w+=ow;expected_e+=oe
        self.assertEqual(w,expected_w);self.assertEqual(e,expected_e)

    def test_workloads_match(self):
        for name,blocks,n in [('dense-32',1,32),('irregular-29',1,29),('dense-2048',64,32)]:
            self.assertEqual(fast.workload(blocks,n),oracle.workload(name))
        for f,k in oracle.LANES[1:]:
            self.compare(np.array(fast.workload(2)['matrix']).reshape(2,1024),f,k)

    def test_random_scale_and_residuals(self):
        rng=np.random.default_rng(41209)
        values=np.ldexp(rng.uniform(-1,1,(8,32)),rng.integers(-100,49,(8,32)))
        values[0,:]=0
        for f,k in oracle.LANES[1:]:self.compare(values,f,k)

    def test_fp4_midpoints_and_neighbors(self):
        mid=np.concatenate([fast.FP4_MID,-fast.FP4_MID])
        values=np.concatenate([mid,np.nextafter(mid,-np.inf),np.nextafter(mid,np.inf)])
        values=np.pad(values,(0,64-len(values)))
        for e in [-48,-1,0,48]:
            a=np.ldexp(values,e).reshape(2,32)
            # Pin the desired block scale by including the maximum.
            a[:,31]=np.ldexp(6.,e)
            for k in [2,4,8]:self.compare(a,4,k)

    def test_tiny_values_and_refusals(self):
        a=np.zeros((1,32));a[0,:4]=[np.nextafter(0.,1.),-np.nextafter(0.,1.),2.**-1000,-2.**-1000]
        for f,k in oracle.LANES[1:]:self.compare(a,f,k)
        for bad in [np.full((1,32),np.nan),np.full((1,32),2.**80),np.zeros((1,31))]:
            with self.assertRaises(ValueError):fast.encode_batch(bad,4,8)

    def test_binary_preserves_all_fields_and_rejects_truncation(self):
        for f,k in oracle.LANES:
            r=fast.request(2,f,k,'legacy' if f==64 else 'columns',n=29)
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'request.bin';fast.write_binary(p,r)
                self.assertEqual(fast.read_binary(p),r)
                p.write_bytes(p.read_bytes()[:-1])
                with self.assertRaises(ValueError):fast.read_binary(p)


class IndependentWindowReference(unittest.TestCase):
    def test_vectorized_original_a_keeps_scalar_accumulation_order(self):
        from lp_fp4_fast_study import reference
        for n in (29,32):
            r=fast.request(2,4,8,n=n,updates=8)
            # The study uses n=32. Keep padding zero in this independent check.
            expected=oracle.reference(r,8)
            actual=reference(r).tolist()
            self.assertEqual(actual,expected)

class RichGridPreparation(unittest.TestCase):
    def test_rich_grid_matches_exact_matrix_oracle(self):
        from lp_fp4_fast_study import request
        for f,k in [(4,8),(8,4),(16,2)]:
            r=request(dict(blocks=1,format=f,components=k,family='rich',backend='hardware'))
            w,e,_,_=oracle.encode(tuple(r['matrix']),f,k)
            self.assertEqual(r['matrix_codes'].tolist(),w)
            self.assertEqual(r['matrix_exponents'].tolist(),e)

if __name__=='__main__':unittest.main()
