"""A later presence check cannot erase failures, bypass a live PID, or excuse overruns."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import lp_sp_pricing_cleanup as cleanup
from lp_sp_pricing_budget import accounting,binding


class CleanupTests(unittest.TestCase):
    def fixture(self,base,overrun=False):
        directory=base/'resources';directory.mkdir();prefix=directory/'failed'
        values={'.reservation.json':dict(phase='admission',cpu_ns=400,gpu_ns=100),
                '.settlement.json':dict(status='refused',cleanup_empty=False,overrun=overrun,cpu_ns=400,gpu_ns=100),
                '.resource.json':dict(result=dict(cleanup=dict(empty=False,remaining=[dict(pid=123,start_ticks=456)]))),
                '.journal.json':dict(active=dict(coordinator=dict(pid=789,start_ticks=101112)))}
        for suffix,value in values.items():Path(str(prefix)+suffix).write_text(json.dumps(value))
        return Path(str(prefix)+'.reservation.json')

    def test_full_charge_remains_and_fresh_gpu_gate_is_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);self.fixture(base)
            with patch.object(cleanup,'BASE',base),patch.object(cleanup,'live',return_value=False):
                cleanup.record('failed')
                self.assertEqual(accounting(base)['admission'],400)
                self.assertEqual(accounting(base,True)['admission'],100)
                with self.assertRaisesRegex(RuntimeError,'fresh CPU'):cleanup.require_cpu_readmission(base)

    def test_missing_or_live_identity_never_reopens_accounting(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);reservation=self.fixture(base)
            with self.assertRaises(RuntimeError):accounting(base)
            with patch.object(cleanup,'BASE',base),patch.object(cleanup,'live',return_value=False):cleanup.record('failed')
            with patch.object(cleanup,'live',return_value=True):
                with self.assertRaisesRegex(RuntimeError,'still present'):cleanup.verify(reservation)

    def test_overrun_and_missing_full_charge_never_get_a_disposition(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);reservation=self.fixture(base,True)
            with self.assertRaisesRegex(RuntimeError,'non-overrun'):cleanup.inputs(reservation)
            receipt=Path(str(reservation).replace('.reservation.','.settlement.'))
            data=json.loads(receipt.read_text());data.update(overrun=False,cpu_ns=399);receipt.write_text(json.dumps(data))
            with self.assertRaisesRegex(RuntimeError,'full charge'):cleanup.inputs(reservation)

    def test_modified_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);reservation=self.fixture(base)
            with patch.object(cleanup,'BASE',base),patch.object(cleanup,'live',return_value=False):
                cleanup.record('failed')
                journal=Path(str(reservation).replace('.reservation.','.journal.'))
                journal.write_text('{}')
                with self.assertRaisesRegex(RuntimeError,'original evidence'):cleanup.verify(reservation)


if __name__=='__main__':unittest.main()
