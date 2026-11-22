"""Only the exact authorized overrun with dead owned identities can be admitted."""
import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import lp_billion_readmission as r
class ReadmissionContracts(unittest.TestCase):
    def fixture(self):
        receipt={'sha256':r.SHA};approval=dict(status='explicitly_authorized',settlement=receipt,user_answer='Approve recovery and increased time',cpu_caps=r.CPU_CAPS,gpu_caps=r.GPU_CAPS)
        cleanup=dict(status='cleanup_verified',settlement=receipt,identities=[dict(still_live=False,identity={'pid':123,'start_ticks':456})])
        return r.IDENTITY+'.settlement.json',receipt,approval,cleanup
    def test_exact_authorized_failure_and_dead_identity(self):
        with patch.object(r,'same_process',return_value=False):r.validate_exception(*self.fixture())
    def test_another_overrun_is_never_covered(self):
        args=list(self.fixture());args[0]='future-failure.settlement.json'
        with self.assertRaisesRegex(ValueError,'unapproved overrun'):r.validate_exception(*args)
        args=list(self.fixture());args[1]={'sha256':'changed'}
        with self.assertRaisesRegex(ValueError,'unapproved overrun'):r.validate_exception(*args)
    def test_live_owned_identity_closes_recovery(self):
        with patch.object(r,'same_process',return_value=True):
            with self.assertRaisesRegex(ValueError,'still live'):r.validate_exception(*self.fixture())
    def test_approval_and_cleanup_must_bind_same_immutable_receipt(self):
        for index in [2,3]:
            args=list(copy.deepcopy(self.fixture()));args[index]['settlement']={'sha256':'different'}
            with self.assertRaisesRegex(ValueError,'binding'):r.validate_exception(*args)
    def test_allocations_cannot_grow_under_old_approval(self):
        args=list(copy.deepcopy(self.fixture()));args[2]['cpu_caps']['development']+=1
        with self.assertRaisesRegex(ValueError,'phase caps'):r.validate_exception(*args)
    def test_missing_fresh_operational_gate_is_fatal(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root,patch.object(r,'BASE',Path(root)):
            with self.assertRaisesRegex(ValueError,'gate missing'):r.passed(r.GPU)
if __name__=='__main__':unittest.main()
