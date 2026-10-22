"""Independent post-study exact residual oracle and corruption checks."""
import copy
from fractions import Fraction as F
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
import lp_refine_evidence_oracle as evidence


class ExactRefineEvidence(unittest.TestCase):
    def test_sparse_original_oracle_matches_independent_admission_fixture(self):
        fixture = json.loads((ROOT/'tests/regression/lp-refine-oracle.json').read_text())
        for case in fixture['cases']:
            result = evidence.Original(case['model']).evaluate(case['v'], case['y'])
            evidence.enclosed(result['merit'], case['expected']['merit'])

    def test_noncontiguous_ids_sense_offset_and_original_activity(self):
        fixture = json.loads((ROOT/'tests/regression/lp-refine-oracle.json').read_text())
        case = copy.deepcopy(next(c for c in fixture['cases'] if len(c['model']['variables']) == 3 and len(c['model']['constraints']) == 2))
        original = evidence.Original(case['model']).evaluate(case['v'], case['y'])
        for variable in case['model']['variables']:
            variable['id'] = 17+3*variable['id']
        for row in case['model']['constraints']:
            row['id'] = 31+2*row['id']
            for term in row['terms']:
                term['variable_id'] = 17+3*term['variable_id']
        for term in case['model']['objective']['terms']:
            term['variable_id'] = 17+3*term['variable_id']
        case['model']['variables'].reverse()
        case['model']['constraints'].reverse()
        self.assertEqual(original, evidence.Original(case['model']).evaluate(case['v'], case['y']))
        case['model']['objective']['offset'] += 3
        changed = evidence.Original(case['model']).evaluate(case['v'], case['y'])
        self.assertEqual(changed['objective'], original['objective']+3)
        self.assertEqual(changed['merit'], original['merit'])

    def test_forged_merit_and_trace_work_are_rejected(self):
        with self.assertRaises(ValueError):
            evidence.enclosed(F(1, 3), dict(lower=0.0, upper=0.3))
        with self.assertRaises(ValueError):
            evidence.verify(None, dict(work=dict(physical_updates=1), trace=[dict(physical_updates=2)]))

    def test_zero_merit_at_exact_box_kkt_point(self):
        def bound(value):
            return dict(kind='finite', value=value)
        model = dict(variables=[dict(id=7, lower=bound(0), upper=bound(2))], constraints=[],
                     objective=dict(sense='minimize', offset=5, terms=[dict(variable_id=7, coefficient=1)]))
        result = evidence.Original(model).evaluate([0.0], [])
        self.assertEqual(result['merit'], 0)
        self.assertEqual(result['objective'], 5)
        self.assertGreater(evidence.Original(model).evaluate([1.0], [])['merit'], 0)


if __name__ == '__main__':
    unittest.main()
