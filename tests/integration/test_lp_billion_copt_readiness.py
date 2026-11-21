"""A setup-only time limit must not stand in for full optimizer workspace admission."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_billion_copt_readiness import workspace_observed
class CoptReadinessContracts(unittest.TestCase):
    def response(self):return dict(solve_called=True,solve_returncode=0,optimal=False,has_solution=False,native={'SimplexIter':0,'BarrierIter':0,'PDLPIter':0})
    def test_returned_setup_only_timeout_is_insufficient(self):self.assertFalse(workspace_observed(self.response()))
    def test_actual_optimization_observes_workspace_even_without_certificate(self):
        r=self.response();r['native']['PDLPIter']=1;self.assertTrue(workspace_observed(r))
    def test_presolve_optimal_requires_strict_accepted_endpoint(self):
        r=self.response();r.update(optimal=True,has_solution=True)
        self.assertFalse(workspace_observed(r));self.assertTrue(workspace_observed(r,True))
    def test_memory_failure_is_not_workspace_admission(self):
        r=self.response();r['native']['PDLPIter']=100;r['solve_returncode']=1;self.assertFalse(workspace_observed(r))
if __name__=='__main__':unittest.main()
