"""Exit races must not invent ownership or hide unexpected sampling failures."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_sp_pricing_guard import physical_pids
from lp_billion_idle import validate_gpu


class OwnershipExitRaces(unittest.TestCase):
    def test_both_process_exit_errors_retain_only_the_observed_pid(self):
        for error in [FileNotFoundError(),ProcessLookupError(3,'No such process')]:
            with patch.object(Path,'read_text',side_effect=error):
                self.assertEqual(physical_pids([dict(pid=123456,start_ticks=8)]),{123456})

    def test_namespace_ids_are_retained_without_inventing_an_owner(self):
        with patch.object(Path,'read_text',return_value='Name:\tworker\nNSpid:\t123456\t88\n'):
            self.assertEqual(physical_pids([dict(pid=88,start_ticks=8)]),{123456,88})

    def test_unexpected_sampling_error_still_fails(self):
        with patch.object(Path,'read_text',side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):physical_pids([dict(pid=88,start_ticks=8)])

    def test_foreign_gpu_process_is_still_rejected(self):
        with self.assertRaisesRegex(Exception,'foreign GPU process'):
            validate_gpu(dict(processes={777:1024},used=1024),{88})


if __name__=='__main__':unittest.main()
