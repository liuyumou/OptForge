"""Scoped development correction; never re-runs the frozen qualification grid."""

from fractions import Fraction as F
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import lp_fp4_contract as contract
import lp_fp4_reference_v2 as corrected


class SeparateErrorBudgets(unittest.TestCase):
    def test_rounding_cancellation_does_not_hide_encoding_remainder(self):
        pair, _ = corrected.pair_round(F(1, 3))
        target = pair - F(1, 1 << 55)
        self.assertEqual(corrected.pair_round(target)[0], pair)
        blocks, bound = corrected.rounded_encode([target], 8)
        represented = corrected.vector_values(blocks, 1)[0]
        encoding = contract.read_rational(blocks[0]['remainder_bound'])
        # This is the minimal compatibility defect in v1's net-error accounting.
        self.assertLess(abs(represented - target), encoding)
        self.assertGreaterEqual(bound, encoding)
        self.assertGreaterEqual(bound, abs(represented - target))

    def test_round_encode_budget_covers_all_blocks_and_components(self):
        values = [F(j - 16, 37) for j in range(35)]
        for components in (2, 4, 8):
            blocks, bound = corrected.rounded_encode(values, components)
            represented = corrected.vector_values(blocks, len(values))
            self.assertGreaterEqual(bound, max(abs(a - b) for a, b in zip(values, represented)))
            self.assertGreaterEqual(bound, max(contract.read_rational(b['remainder_bound']) for b in blocks))

    def test_exact_values_remain_exact_without_extra_error(self):
        blocks, bound = corrected.rounded_encode([F(1, 2), F(-3, 4), F(0)], 8)
        self.assertEqual(bound, 0)
        self.assertEqual(corrected.vector_values(blocks, 3), [F(1, 2), F(-3, 4), 0])


if __name__ == '__main__':
    unittest.main()
