"""The native GPU comparison cannot bypass pinned ownership or memory declarations."""
import os,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import lp_billion_copt_run as copt
class CoptGpuContracts(unittest.TestCase):
    def test_gpu_requires_inherited_pinned_lease_before_vendor_calls(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(ValueError,'inherited pinned'):copt.solve('unused','unused',gpu=True,admission=True)
    def test_soft_memory_limit_must_fit_declared_domain(self):
        for value in [0,-1,float('nan'),float('inf'),48001]:
            with self.assertRaisesRegex(ValueError,'bounded vendor'):copt.solve('unused','unused',memory_mb=value,admission=True)
    def test_scientific_use_requires_source_bound_admission(self):
        with patch.object(copt,'load',return_value={'status':'not_admitted'}):
            with self.assertRaisesRegex(ValueError,'current COPT'):copt.solve('unused','unused')
if __name__=='__main__':unittest.main()
