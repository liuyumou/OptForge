"""Research replay rejects incomplete/broken evidence; no CUDA required."""
import copy
import gzip
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import lp_mixed2_fp4_analysis as a

class Mixed2Fp4(unittest.TestCase):
    def test_exact_interval_has_requested_coverage(self):
        x=a.interval(list(range(32)),.05/64)
        self.assertGreaterEqual(x['coverage'],1-.05/64)
        self.assertEqual(x['n'],32)
        self.assertEqual(x['lower'],x['rank']-1)
        self.assertEqual(x['upper'],32-x['rank'])
    def test_too_few_blocks_give_unbounded_interval(self):
        self.assertIsNone(a.interval([1,2],.05/64)['lower'])
        self.assertIsNone(a.interval([1,2],.05/64)['upper'])
    def test_invalid_samples_are_rejected(self):
        for values in ([],[float('nan')],[float('inf')]):
            with self.assertRaises(ValueError):a.interval(values)
    def test_missing_sessions_are_rejected(self):
        with self.assertRaises(ValueError):a.assess(dict(cells=[dict(id='missing')]),[],{})
    def test_duplicate_cells_are_rejected(self):
        with self.assertRaises(ValueError):a.assess(dict(cells=[dict(id='x'),dict(id='x')]),[],{})
    def test_committed_replay(self):
        # The publication is mandatory acceptance evidence, not an optional fixture.
        d=a.read_archive()
        records={k:v.encode() for k,v in d['records'].items()}
        self.assertEqual(a.assess(d['freeze'],d['sessions'],records,d.get('completion')),a.load(a.ANALYSIS))
        if d.get('completion'):
            bad=copy.deepcopy(d['completion']);bad['missing_cells']=[]
            with self.assertRaises(ValueError):a.assess(d['freeze'],d['sessions'],records,bad)
        altered=dict(records);key=d['sessions'][0]['records'][0]['result']['path'];altered[key]+=b'\n'
        with self.assertRaises(ValueError):a.assess(d['freeze'],d['sessions'],altered,d.get('completion'))

if __name__=='__main__':unittest.main()
