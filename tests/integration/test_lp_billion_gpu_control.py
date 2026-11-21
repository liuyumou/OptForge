"""The explicit assessment extension preserves the entire previous approval chain."""
import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import lp_billion_readmission as r
import test_lp_billion_gpu_packing as packing

class AssessmentAllocationContracts(unittest.TestCase):
    def fixture(self):
        old,revised,previous=packing.RevisedTransferContracts().fixture()
        extension=dict(status='explicitly_authorized',user_answer='Approve assessment/control allocation',
            previous_approval={'path':'approved-packing-transfer-v2.json'},original_approval={'path':'approved-recovery-v1.json'},
            old_cpu_caps=revised['cpu_caps'],old_gpu_caps=revised['gpu_caps'],cpu_caps=r.CPU_CAPS,gpu_caps=r.GPU_CAPS,proposal={},protocol={})
        return copy.deepcopy((old,extension,revised,previous))
    def apply(self,args):
        with patch.object(r,'ref',side_effect=lambda p:{'path':p.name}),patch.object(r,'resolve'):
            return r.assessment_approval(*args)
    def test_only_explicit_extension_admits_exact_caps(self):
        args=self.fixture();out=self.apply(args)
        self.assertEqual(out['settlement'],args[0]['settlement'])
        self.assertEqual(sum(out['cpu_caps'].values()),370000)
        self.assertEqual(sum(out['gpu_caps'].values()),44000)
    def test_missing_authorization_or_changed_caps_fail_closed(self):
        for key,value in [('user_answer',''),('previous_approval',{}),('old_cpu_caps',{}),('cpu_caps',{})]:
            args=list(self.fixture());args[1][key]=value
            with self.assertRaises(ValueError):self.apply(args)
    def test_preceding_approvals_remain_required(self):
        for i in (2,3):
            args=list(self.fixture());args[i]['user_answer']=''
            with self.assertRaises(ValueError):self.apply(args)

class ControlCapacityContracts(unittest.TestCase):
    def test_wide_billion_capacity_includes_original_feasibility_arrays(self):
        from lp_billion_gpu_control_capacity import capacity
        from lp_billion_gpu_pack_capacity import capacity as old
        model=dict(rows=62500000,columns=250000000,nonzeros=1_000_000_000,canonical_tiles=0,covered_nnz=0)
        a,b=old(model),capacity(model)
        expected=8_000_000_000+16*(62500000+250000000)+16*((250000000+1023)//1024)+24
        self.assertEqual(b['gpu_control_extra_bytes'],expected)
        self.assertEqual(b['device_bytes'],a['device_bytes']+expected)
        self.assertGreater(b['host_bytes'],a['host_bytes'])
        self.assertTrue(b['admitted'])
    def test_out_of_capacity_dimensions_remain_refused(self):
        from lp_billion_gpu_control_capacity import capacity
        model=dict(rows=250000000,columns=250000000,nonzeros=1_000_000_000,canonical_tiles=0,covered_nnz=0)
        self.assertFalse(capacity(model)['admitted'])

if __name__=='__main__':unittest.main()
