"""Boundary regression: cap each log, permit a larger bounded evidence file."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from lp_baseline_transport import launch


class Transport(unittest.TestCase):
    def test_large_artifact_with_small_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            code="import resource,pathlib; resource.setrlimit(resource.RLIMIT_FSIZE,(128<<20,128<<20)); pathlib.Path("+repr(str(p/'artifact'))+").write_bytes(b'x'*(17<<20)); print('done')"
            r=launch([sys.executable,'-c',code],os.environ,p/'job',output_limit=256)
            self.assertEqual(r['returncode'],0)
            self.assertEqual((p/'artifact').stat().st_size,17<<20)
            self.assertIsNone(r['exceeded_stream'])

    def test_either_stream_overflow_is_refused_and_bounded(self):
        for descriptor,name in [(1,'stdout'),(2,'stderr')]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)
                r=launch([sys.executable,'-c',f'import os;os.write({descriptor},b"x"*65536)'],os.environ,p/'job',output_limit=256)
                self.assertEqual(r['returncode'],86)
                self.assertEqual(r['exceeded_stream'],name)
                self.assertLessEqual((p/('job.'+name)).stat().st_size,256)


if __name__=='__main__': unittest.main()
