"""Frozen research boundaries, exact rounding and shared accounting."""
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from analyze_lp_rounding import components,power_exponent
from benchmark_lp_research import protocol,jobs,label
from lp_research_budget import category_usage,PRIOR_NS
from lp_protocol import Ledger
class ResearchTests(unittest.TestCase):
    def test_frozen_grid_and_original_targets(self):
        value,base,manifest=protocol();schedule=list(jobs(value,base,manifest))
        self.assertEqual(Counter(j['kind'] for j in schedule),dict(timing=432,profile=48,short=336,trace=24))
        self.assertEqual(len({label(j) for j in schedule}),840)
        self.assertEqual(base['solve']['seed'],17);self.assertEqual(base['order_seed'],17001)
        self.assertEqual(value['prior_gpu_ns'],PRIOR_NS)
        self.assertTrue(all(j['instance']['id'].startswith('gpup-development-') or j['instance']['id'].startswith('ta') for j in schedule))
    def test_three_components_are_exact_and_two_are_not_assumed_exact(self):
        x=1/3;parts=components(x)
        self.assertEqual(sum(map(F,parts)),F(x));self.assertNotEqual(sum(map(F,parts[:2])),F(x))
        self.assertEqual(power_exponent(1.4),0);self.assertEqual(power_exponent(1.5),1)
        self.assertEqual(power_exponent(float.fromhex('0x1p-1074')),-1074)
    def test_acceptance_and_study_share_ledger_with_separate_caps(self):
        with tempfile.TemporaryDirectory() as tmp:
            with Ledger(Path(tmp),'a'*64) as ledger:
                r=ledger.reserve('gpup5b-study-one',2,phase='screening');ledger.settle(r,123)
                r=ledger.reserve('gpup5b-accept-one',2,phase='screening');ledger.settle(r,456)
                self.assertEqual(category_usage(ledger,'study'),123);self.assertEqual(category_usage(ledger,'accept'),456);self.assertEqual(ledger.totals(),579)
    def test_archived_report_is_not_rewritten_by_new_notes(self):
        import subprocess
        path='docs/benchmarks/lp-fp32-slowdown-diagnosis.md'
        old=subprocess.check_output(['git','show','7636845:'+path],cwd=ROOT)
        self.assertEqual((ROOT/path).read_bytes(),old)

    def test_independent_rational_sparse_and_product_fixtures_reproduce(self):
        from lp_research_oracle import generate,verify_products
        from lp_protocol import read_json
        self.assertEqual(generate(),read_json(ROOT/'crates/optimizer-lp/tests/fixtures/research-sparse.json'))
        self.assertEqual(verify_products(),39)
