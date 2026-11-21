"""Phase transfers preserve the exact old exception and all resource ceilings."""
import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import lp_billion_readmission as admission

PACK_CPU=dict(implementation=8000,native=22000,admission=52000,development=140000,reporting=97000,cleanup=1000)
PACK_GPU=dict(admission=7000,development=28000)

class TransferContracts(unittest.TestCase):
    def fixture(self):
        old=dict(cpu_caps=dict(implementation=2000,native=14000,admission=45000,development=148000,reporting=110000,cleanup=1000),gpu_caps=dict(admission=9000,development=26000),settlement={'sha256':admission.SHA})
        transfer=dict(status='explicitly_authorized',user_answer='Approve the phase transfer',previous_approval={'old':True},old_cpu_caps=old['cpu_caps'],old_gpu_caps=old['gpu_caps'],cpu_caps=PACK_CPU,gpu_caps=PACK_GPU,protocol={},proposal={})
        return copy.deepcopy((old,transfer))
    def apply(self,old,transfer):
        with patch.object(admission,'CPU_CAPS',PACK_CPU),patch.object(admission,'GPU_CAPS',PACK_GPU),patch.object(admission,'ref',return_value={'old':True}),patch.object(admission,'resolve'):
            return admission.transfer_approval(old,transfer)
    def test_only_caps_change_under_explicit_transfer(self):
        old,t=self.fixture();result=self.apply(old,t)
        self.assertEqual(result['settlement'],old['settlement'])
        self.assertEqual(sum(result['cpu_caps'].values()),320000)
        self.assertEqual(sum(result['gpu_caps'].values()),35000)
        self.assertEqual(old['gpu_caps']['admission'],9000)
    def test_missing_approval_or_old_binding_is_rejected(self):
        for key,value in [('user_answer',''),('previous_approval',{}),('old_cpu_caps',{})]:
            old,t=self.fixture();t[key]=value
            with self.assertRaises(ValueError):self.apply(old,t)
    def test_unapproved_cap_increase_is_rejected(self):
        old,t=self.fixture();t['gpu_caps']['development']+=1
        with self.assertRaisesRegex(ValueError,'new caps'):self.apply(old,t)


class PackingCapacityContracts(unittest.TestCase):
    def test_gpu_peak_includes_originals_residuals_and_fragments(self):
        from lp_billion_gpu_pack_capacity import capacity
        model=dict(rows=15625000,columns=15625024,nonzeros=1_000_000_000,canonical_tiles=976564,covered_nnz=750000000)
        c=capacity(model)
        self.assertGreater(c['gpu_packing_bytes_upper'],48_000_000_000)
        self.assertGreaterEqual(c['device_bytes'],c['gpu_packing_bytes_upper'])
        self.assertTrue(c['admitted'])
    def test_no_eligible_tiles_need_no_fragment_or_residual_buffers(self):
        from lp_billion_gpu_pack_capacity import capacity
        model=dict(rows=62500000,columns=250000000,nonzeros=1_000_000_000,canonical_tiles=0,covered_nnz=0)
        c=capacity(model)
        self.assertLess(c['gpu_packing_bytes_upper'],26_000_000_000)
        self.assertTrue(c['admitted'])


class RevisedTransferContracts(unittest.TestCase):
    def fixture(self):
        old,previous=TransferContracts().fixture()
        previous['previous_approval']={'path':'approved-recovery-v1.json'}
        # First transfer values are immutable, independent of the current caps.
        previous['cpu_caps']=dict(implementation=6000,native=18000,admission=52000,development=151000,reporting=92000,cleanup=1000)
        previous['gpu_caps']=dict(admission=7000,development=28000)
        transfer=dict(status='explicitly_authorized',user_answer='Approve revised phase transfer',previous_transfer={'path':'approved-packing-transfer-v1.json'},original_approval={'path':'approved-recovery-v1.json'},old_cpu_caps=previous['cpu_caps'],old_gpu_caps=previous['gpu_caps'],cpu_caps=PACK_CPU,gpu_caps=PACK_GPU,protocol={},proposal={})
        return copy.deepcopy((old,transfer,previous))
    def apply(self,args):
        with patch.object(admission,'CPU_CAPS',PACK_CPU),patch.object(admission,'GPU_CAPS',PACK_GPU),patch.object(admission,'ref',side_effect=lambda p:{'path':p.name}),patch.object(admission,'resolve'):
            return admission.revised_transfer_approval(*args)
    def test_revised_transfer_preserves_original_exception(self):
        args=self.fixture();self.assertEqual(self.apply(args)['settlement'],args[0]['settlement'])
    def test_broken_chain_and_missing_second_approval_fail_closed(self):
        for key,value in [('user_answer','Approve the phase transfer'),('original_approval',{}),('old_cpu_caps',{})]:
            args=list(self.fixture());args[1][key]=value
            with self.assertRaises(ValueError):self.apply(args)
    def test_revised_caps_cannot_silently_increase(self):
        args=list(self.fixture());args[1]['cpu_caps']['native']+=1
        with self.assertRaisesRegex(ValueError,'new caps'):self.apply(args)


class PackingReportContracts(unittest.TestCase):
    def test_comparison_ignores_only_diagnostics_not_certificates_or_endpoints(self):
        from lp_billion_gpu_pack_report import canonical
        a=dict(status='limit',certificate={'accepted':False,'gap_upper':1.},endpoint={'primal':{'sha256':'a'}},logical=100,fast_config={'gpu_preparation':True},cost_ns={'execution':1})
        b=copy.deepcopy(a);b['gpu_packing']={'total_ns':100};b['fast_config']['gpu_packing']=True;b['cost_ns']['execution']=2
        self.assertEqual(canonical(a),canonical(b))
        for key,value in [('logical',101),('certificate',{'accepted':True,'gap_upper':0.}),('endpoint',{'primal':{'sha256':'b'}})]:
            c=copy.deepcopy(b);c[key]=value
            self.assertNotEqual(canonical(a),canonical(c))

if __name__=='__main__':unittest.main()
