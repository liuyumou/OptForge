"""Exact inventory-helper identity and bounded wait contracts."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from lp_sp_pricing_nontall_exit import inventory_command,GUARD,finish


class InventoryExitTests(unittest.TestCase):
    def test_only_exact_inventory_command_is_selected(self):
        self.assertTrue(inventory_command(['/python','-B',str(GUARD),'inventory']))
        for argv in ([],['/python','-B',str(GUARD),'idle-exec'],['/python','-B','/different/guard.py','inventory'],['/python',str(GUARD),'inventory']):self.assertFalse(inventory_command(argv))
    def test_original_coordinator_identity_is_required(self):
        with patch('lp_sp_pricing_nontall_exit.still_same_process',return_value=False):
            with self.assertRaisesRegex(RuntimeError,'coordinator disappeared'):finish(dict(pid=123,start_ticks=456),seconds=1)


if __name__=='__main__':unittest.main()
