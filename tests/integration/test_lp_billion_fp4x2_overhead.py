"""CPU-only tests of candidate comparison and fail-closed default promotion."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_billion_fp4x2_evaluate import promotion, semantic


def rows():
    return [dict(family=family,seed=seed,fp4_share=share,exact=True,audited=True,memory_admitted=True,
                 status='certified',reference_ns=120,candidate_ns=100)
            for family,share in [('coupled',.75),('irregular',0)] for seed in [1,2,3]]


class Promotion(unittest.TestCase):
    def test_correctness_before_performance(self):
        self.assertFalse(promotion(rows())['promote'])
        self.assertTrue(promotion(rows(),True)['promote'])
    def test_no_data_or_incomplete_seed_roster(self):
        self.assertFalse(promotion([],True)['promote'])
        self.assertFalse(promotion(rows()[:-1],True)['promote'])
    def test_fallback_and_real_fp4_work_required(self):
        for share in [0,.75]:
            data=rows()
            for row in data:row['fp4_share']=share
            self.assertFalse(promotion(data,True)['promote'])
    def test_failure_and_deadline_never_disappear(self):
        for field,value in [('status','deadline'),('status','missing_response'),('audited',False),('exact',False),('memory_admitted',False),('candidate_ns',0),('candidate_ns',float('nan')),('reference_ns',float('inf'))]:
            data=rows();data[-1][field]=value
            self.assertFalse(promotion(data,True)['promote'])
    def test_family_regression_cannot_hide_in_aggregate(self):
        data=rows()
        for row in data:row['candidate_ns']=30 if row['family']=='coupled' else 130
        self.assertFalse(promotion(data,True)['promote'])
    def test_small_improvement_does_not_promote(self):
        data=rows()
        for row in data:row['candidate_ns']=119
        self.assertFalse(promotion(data,True)['promote'])
    def test_comparison_preserves_signed_zero(self):
        self.assertNotEqual(semantic(dict(certificate=dict(bound=-0.0))),
                            semantic(dict(certificate=dict(bound=0.0))))
    def test_comparison_preserves_rollback_certificate_and_work(self):
        original=dict(status='limit',physical=32,logical=24,certificate=dict(accepted=False,bound=1.),
                      accepted_product_work=[1,1,0,2],endpoint=dict(primal='a',dual='b'),elapsed_ns=100)
        changed=copy.deepcopy(original);changed['elapsed_ns']=50
        self.assertEqual(semantic(original),semantic(changed))
        for field,value in [('logical',32),('certificate',dict(accepted=True,bound=1.)),('endpoint',dict(primal='a',dual='c')),('accepted_product_work',[2,2,0,2])]:
            changed=copy.deepcopy(original);changed[field]=value
            self.assertNotEqual(semantic(original),semantic(changed))


if __name__=='__main__':unittest.main()
