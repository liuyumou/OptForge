"""Implicit primal certificates checked against independent Fraction elimination."""
from fractions import Fraction as Q
from pathlib import Path
import sys
import unittest
import numpy as np
from scipy import sparse
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'))
from sp_pricing.primal_recovery import row_proposal,build
from lp_sp_pricing_primal_proof import verify_arrays

def fixture(m,n,seed,mixed=False):
    rng=np.random.default_rng(seed);a=rng.integers(-7,8,size=(m,n)).astype(float)/8;a[:,:m]+=np.eye(m)*4
    x=rng.integers(-8,9,size=n)/8;y=rng.integers(1,8,size=m)/16
    if mixed:y[::3]=0
    b=a@x+np.where(y==0,.375,0);c=a.T@y
    return sparse.csr_matrix(a),b,c

def exact_solve(a,b):
    rows=[list(map(Q,row))+[Q(rhs)] for row,rhs in zip(a,b)];n=len(rows)
    for j in range(n):
        p=next(i for i in range(j,n) if rows[i][j]);rows[j],rows[p]=rows[p],rows[j];pivot=rows[j][j];rows[j]=[q/pivot for q in rows[j]]
        for i in range(n):
            if i!=j:
                factor=rows[i][j];rows[i]=[q-factor*v for q,v in zip(rows[i],rows[j])]
    return [row[-1] for row in rows]

class ImplicitPrimal(unittest.TestCase):
    def check(self,a,b,c,cert):return verify_arrays(a.indptr,a.indices,a.data,b,c,cert['x0'],cert['y'],cert['columns'],cert['inverse'])
    def test_wide_and_mixed_against_fraction_oracle(self):
        for m,n in ((1,4),(5,13),(8,8)):
            for mixed in (False,True):
                a,b,c=fixture(m,n,126001+m,mixed);x,y,_=row_proposal(a,b,c);cert,_=build(a,b,c,x,y)
                self.assertIsNotNone(cert);proof=self.check(a,b,c,cert);self.assertTrue(proof['accepted']);self.assertEqual(proof['visited_nonzeros'],a.nnz)
                dense=[[Q(float(v)) for v in row] for row in a.toarray()];base=list(map(Q,cert['x0']));cols=list(map(int,cert['columns']))
                rhs=[Q(float(bi))-sum(q*v for q,v in zip(row,base)) for row,bi in zip(dense,b)]
                delta=exact_solve([[row[j] for j in cols] for row in dense],rhs)
                for j,v in zip(cols,delta):base[j]+=v
                self.assertTrue(all(sum(q*v for q,v in zip(row,base))==Q(float(bi)) for row,bi in zip(dense,b)))
                self.assertEqual(sum(Q(float(ci))*v for ci,v in zip(c,base)),sum(Q(float(bi))*Q(float(yi)) for bi,yi in zip(b,cert['y'])))
    def test_accepts_nondyadic_primal(self):
        a=sparse.csr_matrix([[3.,1.],[0.,3.]]);b=np.array([1.,1.]);c=np.array([3.,4.]);x,y,_=row_proposal(a,b,c);cert,_=build(a,b,c,x,y)
        self.assertTrue(self.check(a,b,c,cert)['accepted']);self.assertEqual(exact_solve(a.toarray(),b),[Q(2,9),Q(1,3)])
    def test_rejects_negative_or_wrong_dual(self):
        a,b,c=fixture(5,13,126011);x,y,_=row_proposal(a,b,c);cert,_=build(a,b,c,x,y)
        for changed in (-cert['y'],cert['y']+1/1024):
            self.assertFalse(self.check(a,b,c,dict(cert,y=changed))['accepted'])
    def test_rejects_invalid_inverse_and_columns(self):
        a,b,c=fixture(5,13,126021);x,y,_=row_proposal(a,b,c);cert,_=build(a,b,c,x,y)
        for changed in (dict(inverse=np.zeros((5,5))),dict(columns=np.zeros(5,dtype=np.uint32)),dict(columns=np.arange(5,dtype=np.uint32)+100)):
            self.assertFalse(self.check(a,b,c,dict(cert,**changed))['accepted'])
    def test_rejects_nonfinite_and_noncanonical(self):
        a,b,c=fixture(5,13,126031);x,y,_=row_proposal(a,b,c);cert,_=build(a,b,c,x,y)
        self.assertFalse(self.check(a,b,c,dict(cert,x0=np.full(13,np.nan)))['accepted'])
        a.indices[:2]=a.indices[0];self.assertFalse(self.check(a,b,c,cert)['accepted'])
    def test_rejects_singular_basis(self):
        a=sparse.csr_matrix([[1.,2.,1.],[1.,2.,2.]]);b=np.array([1.,1.]);y=np.ones(2);c=np.asarray(a.T@y)
        self.assertFalse(verify_arrays(a.indptr,a.indices,a.data,b,c,np.zeros(3),y,np.array([0,1]),np.eye(2))['accepted'])
    def test_scalar_basis_and_zero_objective(self):
        a=sparse.csr_matrix([[3.,1.]]);b=np.array([1.]);c=np.zeros(2);cert,_=build(a,b,c,np.zeros(2),np.zeros(1))
        self.assertTrue(self.check(a,b,c,cert)['accepted'])
    def test_shape_cap_precedes_allocations(self):
        with self.assertRaises(ValueError):row_proposal(sparse.csr_matrix((4097,8194)),np.zeros(4097),np.zeros(8194))

if __name__=='__main__':unittest.main()
