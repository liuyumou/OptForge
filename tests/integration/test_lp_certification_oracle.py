"""Independent exact-rational evidence for GPUP-1; no solver/device dependency."""

from fractions import Fraction
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from lp_certification_oracle import FIXTURE, bits, build, directed, render


class CertificationOracle(unittest.TestCase):
    def test_committed_fixtures_reproduce_exact_rational_evaluation(self):
        document = build()
        self.assertEqual(json.loads(FIXTURE.read_text()), document)
        self.assertEqual(FIXTURE.read_text(), render(document))

    def test_directed_rounding_covers_values_between_subnormals(self):
        half = Fraction(1, 2**1075)
        self.assertEqual(directed(half, False), bits(0.0))
        self.assertEqual(directed(half, True), bits(math.ulp(0.0)))
        self.assertEqual(directed(-half, False), bits(-math.ulp(0.0)))
        self.assertEqual(directed(-half, True), bits(-0.0))

    def test_directed_rounding_refuses_to_hide_overflow(self):
        maximum = float.fromhex("0x1.fffffffffffffp+1023")
        self.assertEqual(directed(Fraction(maximum)*2, False), bits(maximum))
        self.assertEqual(directed(Fraction(maximum)*2, True), bits(math.inf))
        self.assertEqual(directed(-Fraction(maximum)*2, False), bits(-math.inf))
        self.assertEqual(directed(-Fraction(maximum)*2, True), bits(-maximum))

    def test_cancellation_counterexample_has_the_known_exact_bound(self):
        cases = {case["name"]: case for case in build()["programs"]}
        exact = Fraction(-152587890625, 549755813888)
        self.assertEqual(cases["cancellation-minimize"]["exact_bound"], bits(float(exact)))
        self.assertEqual(cases["cancellation-maximize"]["exact_bound"], bits(float(-exact)))
