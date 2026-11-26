"""Certificate trust-boundary, full exact oracle and adversarial tests."""
from fractions import Fraction as Q
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
from scipy import sparse
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'));sys.path.insert(0,str(ROOT/'tools'))
from sp_pricing.geometry_fast import exact_certificate,dyadic_integers
from sp_pricing.certificate_guard import guarded_certificate
from lp_sp_pricing_scale_verify import verify_arrays,check
from lp_sp_pricing_verify import verify
from lp_billion_arrays import write


class CertificateReliabilityTests(unittest.TestCase):
    def test_128_mixed_active_models_match_two_independent_oracles(self):
        for seed in range(128):
            rng=np.random.default_rng(122201+seed);m,n=3+seed%9,2+seed%7
            a=sparse.csr_matrix(rng.integers(-8,9,size=(m,n)).astype(float)/16)
            xi=rng.integers(-8,9,size=n,dtype=np.int64);yi=rng.integers(0,8,size=m,dtype=np.int64)
            x=xi/8;y=yi/128;slack=np.where(yi==0,rng.integers(1,8,size=m)/8,0.);b=a@x+slack;c=np.asarray(a.T@y)
            self.assertTrue(guarded_certificate(a,b,c,xi,3,yi,7))
            independent=verify_arrays(a.indptr,a.indices,a.data,b,c,list(map(Q,x)),list(map(Q,y)))
            self.assertTrue(independent['accepted']);self.assertEqual(independent['visited_nonzeros'],a.nnz)
            self.assertTrue(verify(dict(A=a.toarray().tolist(),b=b.tolist(),c=c.tolist()),dict(status='optimal',x=x.tolist(),y=y.tolist()))['accepted'])
    def test_384_deliberate_proof_faults_are_rejected(self):
        for seed in range(128):
            rng=np.random.default_rng(122501+seed);a=sparse.csr_matrix(rng.integers(1,8,size=(6,4)).astype(float)/16)
            xi=rng.integers(-4,5,size=4,dtype=np.int64);yi=rng.integers(1,8,size=6,dtype=np.int64)
            x=xi/8;y=yi/128;b=a@x;c=np.asarray(a.T@y)
            for kind in ('primal','dual_sign','objective'):
                xx=xi.copy();yy=yi.copy();cc=c.copy()
                if kind=='primal':xx[0]+=1
                elif kind=='dual_sign':yy[0]=-1
                else:cc[0]+=2**-20
                self.assertFalse(guarded_certificate(a,b,cc,xx,3,yy,7))
                self.assertFalse(verify_arrays(a.indptr,a.indices,a.data,b,cc,list(map(Q,xx/8)),list(map(Q,yy/128)))['accepted'])
    def test_unsigned_wrap_is_rejected_before_narrowing(self):
        a=sparse.csr_matrix([[-1.]]);b=np.array([1.]);c=np.array([-1.]);x=np.array([2**64-1],dtype=np.uint64);y=np.array([1],dtype=np.int64)
        # Retained old helper assumes its internal signed/limited input contract.
        self.assertTrue(exact_certificate(a,b,c,x,0,y,0))
        self.assertFalse(guarded_certificate(a,b,c,x,0,y,0))
        self.assertFalse(verify_arrays(a.indptr,a.indices,a.data,b,c,[int(x[0])],[1])['accepted'])
    def test_cached_integer_model_cannot_replace_original_coefficients(self):
        a=sparse.eye(2,format='csr');b=np.ones(2);c=np.ones(2);v=np.ones(2,dtype=np.int64)
        forged=(0,[np.zeros(2,dtype=np.int64)]*3)
        self.assertFalse(guarded_certificate(a,b,c,v,0,v,0,forged))
        self.assertTrue(guarded_certificate(a,b,c,v,0,v,0,dyadic_integers([a.data,b,c])))
    def test_wide_exact_cancellation_and_unsupported_ranges(self):
        a=sparse.csr_matrix([[float(2**40),-float(2**40)]]);b=np.zeros(1);c=np.zeros(2);x=np.full(2,2**40,dtype=np.int64);y=np.zeros(1,dtype=np.int64)
        self.assertTrue(guarded_certificate(a,b,c,x,0,y,0))
        self.assertTrue(verify_arrays(a.indptr,a.indices,a.data,b,c,list(map(int,x)),[0])['accepted'])
        self.assertFalse(guarded_certificate(a,b,c,x+1,0,y,0))
        self.assertFalse(guarded_certificate(a,b,c,x,25,y,0))
    def test_independent_checker_supports_non_dyadic_certificates(self):
        a=sparse.csr_matrix([[3.]])
        self.assertTrue(verify_arrays(a.indptr,a.indices,a.data,np.array([1.]),np.array([6.]),[Q(1,3)],[Q(2)])['accepted'])
    def fixture(self,root):
        arrays={k:write(root,v,t) for k,v,t in [('values',[1.],'f64le'),('offsets',[0,1],'u64le'),('indices',[0],'u32le'),
            ('row_upper',[1.],'f64le'),('row_lower',[-np.inf],'f64le'),('column_lower',[-np.inf],'f64le'),('column_upper',[np.inf],'f64le'),
            ('objective_indices',[0],'u32le'),('objective_values',[1.],'f64le')]}
        model=root/'model.json';model.write_text(json.dumps(dict(schema_version=1,rows=1,columns=1,nonzeros=1,sense='maximize',offset=0.,arrays=arrays)))
        response=root/'response.json';response.write_text(json.dumps(dict(certificate=dict(status='optimal',x=[1],y=[1]),
            endpoint=dict(primal=write(root,[1.]),dual=write(root,[-1.])))))
        return model,response,arrays
    def test_corrupt_original_chunk_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);m,r,arrays=self.fixture(root);self.assertTrue(check(m,r,root)['accepted'])
            chunk=root/'objects'/(arrays['values']['chunks'][0]['sha256']+'.bin');raw=bytearray(chunk.read_bytes());raw[0]^=1;chunk.write_bytes(raw)
            with self.assertRaises(Exception):check(m,r,root)
    def test_published_endpoint_must_match_exact_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);m,r,_=self.fixture(root);d=json.loads(r.read_text());d['endpoint']['primal']=write(root,[np.nextafter(1.,2.)]);r.write_text(json.dumps(d))
            self.assertFalse(check(m,r,root)['accepted'])


if __name__=='__main__':unittest.main()
