"""A stuck owned vendor child must finish cleanup before the outer job deadline."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_billion_owned_process import execute
class OwnedProcessContracts(unittest.TestCase):
    def test_success_preserves_output(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'out';r=execute([sys.executable,'-c','print("retained")'],out,Path(d)/'err',5)
            self.assertEqual(r['returncode'],0);self.assertFalse(r['timed_out']);self.assertEqual(out.read_text(),'retained\n')
    def test_timeout_reaps_only_direct_child(self):
        with tempfile.TemporaryDirectory() as d:
            r=execute([sys.executable,'-c','import time; time.sleep(30)'],Path(d)/'out',Path(d)/'err',.05)
            self.assertTrue(r['timed_out']);self.assertIsNotNone(r['returncode']);self.assertFalse(Path('/proc',str(r['pid'])).exists())
    def test_failure_is_not_disguised_as_timeout(self):
        with tempfile.TemporaryDirectory() as d:
            r=execute([sys.executable,'-c','raise SystemExit(3)'],Path(d)/'out',Path(d)/'err',5)
            self.assertEqual(r['returncode'],3);self.assertFalse(r['timed_out'])
if __name__=='__main__':unittest.main()
