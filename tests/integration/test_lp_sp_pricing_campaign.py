"""Regression contracts for untouched-cell recovery and bounded launch admission."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import lp_sp_pricing_recover as recovery


class RecoveryTests(unittest.TestCase):
    def test_pending_never_restarts_existing_or_unsupported_cells(self):
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary);(out/'cells').mkdir();(out/'cells'/'old').mkdir()
            f=dict(cells=[dict(id='old',lane='practical',status='pending'),
                          dict(id='cpu',lane='practical',status='pending'),
                          dict(id='gpu',lane='copt_scale_off',status='pending'),
                          dict(id='unsupported',lane='practical',status='unsupported_capacity')])
            self.assertEqual([c['id'] for c in recovery.pending(f,out,False)],['cpu'])
            self.assertEqual([c['id'] for c in recovery.pending(f,out,True)],['gpu'])

    def test_worker_does_not_start_a_cell_without_its_full_window_and_cleanup_margin(self):
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary);(out/'cells').mkdir()
            f=dict(cells=[dict(id='never-started',lane='practical',status='pending',model_index=0)],
                   models=[dict(outer_seconds=60)],configuration={})
            with patch.object(recovery,'validated',return_value=f),patch.object(recovery,'launch') as launch:
                recovery.worker(out/'freeze.json',False,94,'bounded')
                launch.assert_not_called()
            self.assertFalse((out/'cells'/'never-started').exists())

    def test_failed_chunk_stops_before_another_reservation(self):
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary);(out/'cells').mkdir()
            f=dict(cells=[dict(id='untouched',lane='practical',status='pending')])
            totals={phase:0 for phase in recovery.CPU}
            with patch.object(recovery,'validated',return_value=f),patch.object(recovery,'accounting',return_value=totals),\
                 patch.object(recovery,'run',return_value=dict(status='refused')) as run:
                with self.assertRaisesRegex(RuntimeError,'chunk failed'):
                    recovery.execute(out/'freeze.json')
                self.assertEqual(run.call_count,1)


if __name__=='__main__':unittest.main()
