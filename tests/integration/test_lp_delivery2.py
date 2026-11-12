"""DELIVERY2 evidence, immutable numerical bodies and allocation admission."""
import copy
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from lp_delivery2_transport import deliver
from lp_delivery2_cpu import numerical_source
from lp_delivery2_study import matches
from lp_delivery2_budget import admission_open
from test_lp_fp4_checker import sample

class DeliveryGuards(unittest.TestCase):
    def test_numerical_state_machine_is_retained_exactly(self):
        self.assertTrue(numerical_source()['unchanged'])

    def test_checkpoint_signed_zero_cannot_disappear(self):
        old=sample();old['checkpoint']={'raw':[-0.0]}
        new=copy.deepcopy(old);new['checkpoint']['raw'][0]=0.0
        with self.assertRaises(ValueError):matches(new,old,{'sha256':'old'})
        matches(old,old,{'sha256':'old'})

    def test_failed_delivery_preserves_bytes_without_a_successful_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(subprocess.CalledProcessError):
                deliver([sys.executable,'-c','import sys; print("partial"); print("error",file=sys.stderr); sys.exit(7)'],root/'failed',root/'log',3)
            self.assertEqual((root/'failed').read_bytes(),b'partial\n')
            self.assertEqual((root/'log').read_bytes(),b'error\n')
            with self.assertRaises(subprocess.TimeoutExpired):
                deliver([sys.executable,'-c','import sys,time; print("started",flush=True); time.sleep(30)'],root/'timeout',root/'timeout-log',.5)
            self.assertFalse((root/'timeout').exists())
            self.assertEqual((root/'timeout.partial').read_bytes(),b'started\n')

    def test_unsettled_or_closed_allocation_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'resources').mkdir();admission_open(root)
            (root/'resources/a.reservation.json').write_text('{}')
            with self.assertRaises(ValueError):admission_open(root)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'CLOSED.json').write_text('{}')
            with self.assertRaises(ValueError):admission_open(root)

if __name__=='__main__':unittest.main()
