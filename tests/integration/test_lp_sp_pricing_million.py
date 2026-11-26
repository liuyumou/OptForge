"""Structural contracts for the large-input experiment, without GPU work."""
import sys
from pathlib import Path
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lp_sp_pricing_million import matrix, capacity, ORIGINAL, AUX


class MillionProtocol(unittest.TestCase):
    def test_canonical_exact_nnz_and_dyadic_coefficients(self):
        for m, n, k in [(17, 19, 7), (7, 7, 7), (12, 5, 1)]:
            a = matrix(m, n, k, 1201)
            self.assertEqual(a.nnz, m*k)
            self.assertTrue(a.has_canonical_format)
            self.assertTrue(np.all(a.data > 0))
            np.testing.assert_array_equal(a.data*16, np.rint(a.data*16))

    def test_planted_solution_is_exactly_complementary(self):
        a = matrix(16, 12, 5, 1203)
        x = np.ones(12); y = np.ones(16)/16
        b, c = a @ x, a.T @ y
        self.assertEqual(float(c @ x), float(b @ y))
        np.testing.assert_array_equal(a.T @ y, c)

    def test_scale_names_are_not_confused_with_nonzeros(self):
        self.assertTrue(all(c['m']*c['degree'] == 1000000 for c in ORIGINAL))
        self.assertTrue(all(c['r']*c['s'] == 1000000 for c in AUX))
        self.assertEqual(AUX[-1]['r']*AUX[-1]['degree'], 16000)

    def test_current_candidate_refusals_are_explicit(self):
        for c in ORIGINAL:
            self.assertEqual(capacity(c['m'], c['n'])['reason'], 'explicit_reference_geometry_limit')
        self.assertIsNone(capacity(20, 20)['reason'])
        self.assertEqual(capacity(800, 2)['reason'], 'paired_basis_fill_limit')

    def test_deterministic_generation_and_shape_validation(self):
        a, b = matrix(13, 17, 9, 1), matrix(13, 17, 9, 1)
        np.testing.assert_array_equal(a.data, b.data)
        np.testing.assert_array_equal(a.indices, b.indices)
        for args in [(0, 1, 1), (1, 1, 2), (1, 1, 0)]:
            with self.assertRaises(ValueError): matrix(*args, 1)


if __name__ == '__main__': unittest.main()
