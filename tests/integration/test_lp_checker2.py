"""Prospective pairing and incomplete-cohort decision contracts."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_checker2_study import cells
from lp_checker2_analysis import summarize

class Checker2StudyTests(unittest.TestCase):
    def test_balanced_full_roster(self):
        roster=cells(16,420075)
        self.assertEqual(len(roster),512)
        self.assertEqual(len({c['id'] for c in roster}),512)
        for key in {(c['family'],c['tier'],c['lane']) for c in roster}:
            rows=[c for c in roster if (c['family'],c['tier'],c['lane'])==key]
            self.assertEqual(sum(c['variant']=='baseline' and c['position']==0 for c in rows),8)
            for block in range(16):
                pair=[c for c in rows if c['block']==block]
                self.assertEqual({c['variant'] for c in pair},{'baseline','candidate'})
                self.assertEqual({c['position'] for c in pair},{0,1})
    def test_missing_pairs_never_pass(self):
        pair=({'complete_session_ns':2_000_000_000},{'complete_session_ns':1_000_000_000})
        self.assertFalse(summarize([pair]*15)['scoped_pass'])
        self.assertFalse(summarize([pair]*15)['provisional_pass'])
        self.assertTrue(summarize([pair]*16)['scoped_pass'])
    def test_absolute_value_floor_and_regression(self):
        pairs=[({'complete_session_ns':20_000_000},{'complete_session_ns':15_000_000})]*16
        self.assertFalse(summarize(pairs)['scoped_pass'])
        self.assertFalse(summarize(pairs)['provisional_pass'])
        pairs=[({'complete_session_ns':1_000_000_000},{'complete_session_ns':2_000_000_000})]*16
        self.assertFalse(summarize(pairs)['scoped_pass'])
    def test_no_pairs_is_explicit(self):
        r=summarize([]);self.assertEqual(r['missing_pairs'],16);self.assertFalse(r['scoped_pass'])
if __name__=='__main__':unittest.main()
