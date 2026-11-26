"""The freeze preflight must not treat its own CPU reservation as an LP run."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import lp_sp_pricing_gpu_opt_compare as compare


class ComparisonAccounting(unittest.TestCase):
    def test_active_admission_and_failed_confirmation_charge(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);resources=base/'resources';resources.mkdir()
            def write(name,value):(resources/name).write_text(json.dumps(value))
            write('freeze.reservation.json',dict(phase='admission'))
            write('old.reservation.json',dict(phase='confirmation'))
            write('old.settlement.json',dict(status='refused',cleanup_empty=True,overrun=False,cpu_ns=400,gpu_ns=100))
            with patch.object(compare,'BASE',base):
                self.assertEqual(compare.confirmation_usage(),400)
                self.assertEqual(compare.confirmation_usage(True),100)
                write('pending.reservation.json',dict(phase='confirmation'))
                with self.assertRaisesRegex(RuntimeError,'still active'):compare.confirmation_usage()


if __name__=='__main__':unittest.main()
