"""Independent exact contracts for native geometry and certified factor proposals."""
from fractions import Fraction as Q
from pathlib import Path
import sys
import unittest
import numpy as np
from scipy import sparse
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'));sys.path.insert(0,str(ROOT/'tools'))
from sp_pricing.geometry_fast import native_rref,rank_proof,exact_certificate,certified_factor_proposal,FastGeometrySolver
from sp_pricing.compact_basis import Rows,Storage,sparse_rref
from sp_pricing.exact import Work,Limit
from lp_sp_pricing_verify import verify

def work():return Work(seconds=30,max_operations=100000000)

class NativeGeometryTests(unittest.TestCase):
 def test_native_sparse_rref_matches_fraction_reference(self):
  for seed in range(24):
   rng=np.random.default_rng(seed);a=rng.integers(-4,5,size=(5,8))
   if seed%2:a[-1]=a[0]
   source=Rows.dense([[Q(int(v),1+(seed%3)) for v in row] for row in a])
   old,p=sparse_rref(source.rows,8,work(),Storage());new,q=native_rref(source.rows,8,work(),Storage())
   self.assertEqual((new.rows,q),(old.rows,p))
 def test_augmented_inconsistency_and_pivot_order(self):
  source=Rows.dense([[0,0,3],[0,1,2],[1,0,4],[0,0,6]])
  old,p=sparse_rref(source.rows,3,work(),Storage(),2);new,q=native_rref(source.rows,3,work(),Storage(),2)
  self.assertEqual((new.rows,q),(old.rows,p))
 def test_native_limits_and_dimensions(self):
  a=Rows.dense([[1,2,3],[3,2,1]])
  with self.assertRaisesRegex(Limit,'storage'):native_rref(a.rows,3,work(),Storage(entries=2))
  with self.assertRaisesRegex(Limit,'operation'):native_rref(a.rows,3,Work(max_operations=8),Storage())
  with self.assertRaisesRegex(ArithmeticError,'native_geometry_4'):native_rref([{4:Q(1)}],2,work(),Storage())
 def test_modular_rank_is_only_a_positive_certificate(self):
  for a,expected in [([[0,1],[1,0]],True),([[1,2],[2,4]],False),([[65521,0],[0,1]],False)]:
   got,info=rank_proof(Rows.dense(a).rows,2,work());self.assertEqual(got,expected)
  got,info=rank_proof([{0:Q(1,65521)}],1,work());self.assertFalse(got);self.assertEqual(info['reason'],'noninvertible_denominator')
  self.assertTrue(all(65521%d for d in range(2,257)))
 def test_integer_certificate_against_independent_original_verifier(self):
  for seed in range(16):
   rng=np.random.default_rng(seed);a=rng.integers(-10,11,size=(9,5))/16
   xv=rng.integers(-8,9,size=5,dtype=np.int64);yv=rng.integers(1,8,size=9,dtype=np.int64)
   x=xv/4;y=yv/8;b=a@x;c=a.T@y
   self.assertTrue(exact_certificate(sparse.csr_matrix(a),b,c,xv,2,yv,3))
   model=dict(A=a.tolist(),b=b.tolist(),c=c.tolist());proof=dict(status='optimal',x=list(map(Q,x)),y=list(map(Q,y)))
   self.assertTrue(verify(model,dict(certificate=proof))['accepted'])
   self.assertFalse(exact_certificate(sparse.csr_matrix(a),b,c+1/4096,xv,2,yv,3))
 def test_bad_exact_endpoint_and_ranges(self):
  a=sparse.eye(2,format='csr');b=c=np.ones(2);v=np.ones(2,dtype=np.int64)
  with self.assertRaises(ValueError):exact_certificate(a,b,c,v[:1],0,v,0)
  with self.assertRaises(ValueError):exact_certificate(a,b,c,v.astype(float),0,v,0)
  self.assertFalse(exact_certificate(a,b,c,v,0,-v,0))
  self.assertFalse(exact_certificate(a,b,c,v*(2**41),0,v,0))
 def test_certified_factor_recovery_has_no_construction_witness(self):
  rng=np.random.default_rng(122117);a=rng.integers(-4,5,size=(12,12)).astype(float);a+=np.eye(12)*30
  x=rng.integers(-8,9,size=12)/8;y=rng.integers(1,8,size=12)/16;b=a@x;c=a.T@y
  result,info=certified_factor_proposal(sparse.csr_matrix(a),b,c,work())
  self.assertTrue(info['accepted']);self.assertTrue(verify(dict(A=a.tolist(),b=b.tolist(),c=c.tolist()),dict(certificate=result))['accepted'])
 def test_native_pricing_retains_three_original_outcomes(self):
  for model in [dict(A=[[1],[-1]],b=[2,0],c=[1]),dict(A=[[1],[-1]],b=[0,-1],c=[1]),dict(A=[[-1]],b=[0],c=[1])]:
   result=FastGeometrySolver(work=work(),extra_experts=0,max_queries=64,market_backend='flow').solve(model)
   self.assertTrue(verify(model,result)['accepted'])

if __name__=='__main__':unittest.main()
