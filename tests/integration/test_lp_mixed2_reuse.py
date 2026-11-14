"""State identity and prospective sampling contracts; no device execution."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_mixed2_reuse_confirmation import roster, FAMILIES, TIERS
from lp_mixed2_reuse_admit import numerical
from lp_mixed2_fp4_analysis import interval
from lp_mixed2_reuse_analysis import assess


class ReuseContracts(unittest.TestCase):
    def test_replay_rejects_missing_or_duplicate_sessions(self):
        frozen=dict(cells=[dict(id='one')])
        with self.assertRaises(ValueError):assess(frozen,[],{},[])
        with self.assertRaises(ValueError):assess(frozen,[dict(id='one'),dict(id='one')],{},[])

    def test_replay_rejects_partial_request_roster(self):
        frozen=dict(cells=[dict(id='one')],count=32)
        with self.assertRaises(ValueError):assess(frozen,[dict(id='one',count=32,records=[])],{},[])

    def test_frozen_pairs_are_complete_and_order_balanced(self):
        cells=roster();self.assertEqual(len(cells),512)
        self.assertEqual(len({c['id'] for c in cells}),512)
        for f in FAMILIES:
            for t in TIERS:
                for lane in ['native','fp4x2']:
                    chosen=[c for c in cells if (c['family'],c['tier'],c['lane'])==(f,t,lane)]
                    self.assertEqual(sorted(c['block'] for c in chosen),list(range(32)))
                    self.assertEqual(sum(c['position']==0 for c in chosen),16)

    def test_reproducible_roster_rejects_unbalanced_size(self):
        self.assertEqual(roster(),roster())
        self.assertNotEqual(roster(seed=1),roster(seed=2))
        with self.assertRaises(ValueError):roster(31)

    def test_simultaneous_sample_size_is_session_based(self):
        ci=interval(list(range(32)),.05/16)
        self.assertGreaterEqual(ci['coverage'],1-.05/16)
        self.assertGreater(ci['rank'],0)
        self.assertEqual(ci['n'],32)

    def test_differential_keeps_signed_zero_and_certificate_authority(self):
        keys=('status certified lane final_lane tier window_max fixed_audit physical logical '
              'attempted model_sha256 row_scale shift endpoint certificate audits events checkpoint terminal').split()
        r={k:None for k in keys};r.update(endpoint={'x':0.},certificate={'accepted':True,'checker_binary_sha256':'old'},
                                        events=[{'step':{'gpu_us':1.,'done':2}}])
        other=copy.deepcopy(r);other['events'][0]['step']['gpu_us']=2.
        other['certificate']['checker_binary_sha256']='new'
        self.assertEqual(numerical(r),numerical(other))
        other['endpoint']['x']=-0.;self.assertNotEqual(numerical(r),numerical(other))
        other=copy.deepcopy(r);other['certificate']['accepted']=False
        self.assertNotEqual(numerical(r),numerical(other))


if __name__=='__main__':unittest.main()
