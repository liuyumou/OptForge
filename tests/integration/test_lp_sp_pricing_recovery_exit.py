"""A completed owned cycle is required; never invent observations or ownership."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
import lp_sp_pricing_recovery_exit as subject

class RecoveryExitTests(unittest.TestCase):
    def test_original_coordinator_required(self):
        with patch.object(subject,'still_same_process',return_value=False):
            with self.assertRaisesRegex(RuntimeError,'coordinator disappeared'):subject.finish(dict(pid=1,start_ticks=2))
    def test_empty_window_does_not_replace_observed_complete_cycle(self):
        helper=dict(pid=3,start_ticks=4,ppid=1,inventory=True)
        with patch.object(subject,'still_same_process',return_value=True),patch.object(subject,'helpers',side_effect=[[],[helper],[helper],[]]) as poll,patch.object(subject.time,'sleep'):
            result=subject.finish(dict(pid=1,start_ticks=2))
        self.assertEqual(poll.call_count,4);self.assertEqual(result['observed_helpers'],[helper]);self.assertEqual(result['signals_sent'],0)
    def test_no_inventory_cycle_times_out(self):
        with patch.object(subject,'still_same_process',return_value=True),patch.object(subject,'helpers',return_value=[]):
            with self.assertRaises(TimeoutError):subject.finish(dict(pid=1,start_ticks=2),seconds=0)
