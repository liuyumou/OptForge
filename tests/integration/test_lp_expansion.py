"""GPUP-REP exact storage, arithmetic-oracle and preparation acceptance."""

from dataclasses import replace
import ast
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import lp_expansion_candidate as candidate
import lp_expansion_oracle as oracle


FIXTURE = ROOT / "tests/regression/lp-expansion-oracle-v1.json"


class ExpansionOracleTests(unittest.TestCase):
    """Independent-oracle and complete primitive checks."""

    def test_oracle_fixture_reproduces_and_candidate_agrees(self):
        self.assertEqual(FIXTURE.read_text(), oracle.encoded_fixture())
        counts = candidate.verify_fixture(FIXTURE)
        document = json.loads(FIXTURE.read_text())
        overflow_safe = [case for case in document["primitive_cases"] if case.get("purpose") == "finite result despite overflowing separately rounded product"]
        self.assertEqual(len(overflow_safe), 2)
        self.assertTrue(all(not case["result"]["infinity_sign"] for case in overflow_safe))
        self.assertEqual(
            counts,
            {
                "codec_cases": 32852,
                "primitive_cases": 1058,
                "reduction_cases": 40,
                "comparison_cases": 40,
                "projection_cases": 80,
                "seed": 17004,
            },
        )

    def test_candidate_and_oracle_share_no_arithmetic_helpers(self):
        candidate_source = (ROOT / "tools/lp_expansion_candidate.py").read_text()
        oracle_source = (ROOT / "tools/lp_expansion_oracle.py").read_text()
        candidate_imports = {node.names[0].name for node in ast.walk(ast.parse(candidate_source)) if isinstance(node, ast.Import)}
        candidate_from = {node.module for node in ast.walk(ast.parse(candidate_source)) if isinstance(node, ast.ImportFrom)}
        self.assertNotIn("fractions", candidate_imports)
        self.assertNotIn("fractions", candidate_from)
        oracle_imports = {node.names[0].name for node in ast.walk(ast.parse(oracle_source)) if isinstance(node, ast.Import)}
        oracle_from = {node.module for node in ast.walk(ast.parse(oracle_source)) if isinstance(node, ast.ImportFrom)}
        self.assertNotIn("lp_expansion_candidate", oracle_imports)
        self.assertNotIn("lp_expansion_candidate", oracle_from)
        self.assertNotIn("lp_expansion_oracle", candidate_imports)
        self.assertNotIn("lp_expansion_oracle", candidate_from)

    def test_fixture_corruption_and_understated_error_fail(self):
        document = json.loads(FIXTURE.read_text())
        corrupted = copy.deepcopy(document)
        corrupted["primitive_cases"][0]["result"]["coefficient"] += 1
        understated = copy.deepcopy(document)
        inexact = next(
            case
            for case in understated["primitive_cases"]
            if case["result"]["error_exponent"] is not None
        )
        inexact["result"]["error_exponent"] -= 1
        with tempfile.TemporaryDirectory() as temporary:
            for name, value in (("corrupt", corrupted), ("understated", understated)):
                path = Path(temporary) / f"{name}.json"
                path.write_text(json.dumps(value))
                with self.assertRaises(candidate.ArithmeticRefusal):
                    candidate.verify_fixture(path)

    def test_interrupted_reduction_does_not_return_partial_result(self):
        class CancelledValues:
            def __bool__(self):
                return True

            def __iter__(self):
                yield candidate.Rounded(1, 0)
                raise candidate.ArithmeticRefusal("cancelled")

        with self.assertRaisesRegex(candidate.ArithmeticRefusal, "cancelled"):
            candidate.reduce_sum(CancelledValues(), candidate.EXPANSION64)

    def test_signed_zero_and_arithmetic_exceptions_are_explicit(self):
        positive_zero = candidate.Rounded()
        negative_zero = candidate.Rounded(zero_sign=1)
        negative_one = candidate.Rounded(-1, 0)
        self.assertEqual(candidate.negate(positive_zero).zero_sign, 1)
        self.assertEqual(candidate.absolute(negative_zero).zero_sign, 0)
        self.assertEqual(
            candidate.multiply(positive_zero, negative_one, candidate.BINARY64).zero_sign,
            1,
        )
        self.assertEqual(
            candidate.divide(candidate.Rounded(1, 0), positive_zero, candidate.BINARY64).flags,
            ("divide_by_zero",),
        )
        self.assertEqual(
            candidate.divide(positive_zero, positive_zero, candidate.BINARY64).flags,
            ("invalid",),
        )
        self.assertEqual(
            candidate.square_root(negative_one, candidate.EXPANSION64).flags,
            ("invalid",),
        )


class ExactCodecTests(unittest.TestCase):
    """Canonical finite binary64 and positional expansion codecs."""

    def test_binary64_codec_covers_signed_zero_subnormal_and_maximum(self):
        for bits in (0, 1 << 63, 1, (1 << 63) | 1, 0x0010000000000000, 0x7FEFFFFFFFFFFFFF):
            encoded = candidate.encode_binary64(bits)
            self.assertEqual(candidate.decode_binary64(encoded), bits)
        with self.assertRaisesRegex(candidate.ArithmeticRefusal, "nonfinite_input"):
            candidate.encode_binary64(0x7FF0000000000000)

    def test_codec_rejects_noncanonical_and_malformed_tuples(self):
        encoded = candidate.encode_binary64(0x3FF0000000000001)
        with self.assertRaises(candidate.ArithmeticRefusal):
            candidate.decode_binary64(replace(encoded, tail=9))
        one = candidate.encode_binary64(0x3FF0000000000000)
        with self.assertRaisesRegex(candidate.ArithmeticRefusal, "codec_noncanonical"):
            candidate.decode_binary64(replace(one, high_bits=0x3F800000, exponent=0))
        negative_zero = candidate.encode_binary64(1 << 63)
        with self.assertRaisesRegex(candidate.ArithmeticRefusal, "codec_noncanonical_zero"):
            candidate.decode_binary64(replace(negative_zero, low_bits=1))

    def test_positional_chunks_retain_all_64_significand_bits(self):
        values = (
            candidate.Rounded((1 << 63) | 1, -63),
            candidate.Rounded((1 << 64) - 1, -1085),
            candidate.Rounded(-((1 << 63) | (1 << 23) | 1), 960),
        )
        for value in values:
            document = candidate.expansion_chunks(value)
            self.assertEqual(candidate.decode_expansion_chunks(document), value)
        malformed = candidate.expansion_chunks(values[0])
        malformed["chunks"][2] = 1 << 16
        with self.assertRaisesRegex(candidate.ArithmeticRefusal, "expansion_chunk2"):
            candidate.decode_expansion_chunks(malformed)
        shifted = {"sign": 0, "chunks": [0, 0, 1], "exponent": 1}
        with self.assertRaisesRegex(
            candidate.ArithmeticRefusal, "expansion_noncanonical_significand"
        ):
            candidate.decode_expansion_chunks(shifted)
        with self.assertRaisesRegex(
            candidate.ArithmeticRefusal, "expansion_noncanonical_significand"
        ):
            candidate.expansion_chunks(candidate.Rounded(1, -63))
        normalized = candidate.normalize(candidate.Rounded(1, -63), candidate.EXPANSION64)
        self.assertEqual(normalized, candidate.Rounded(1 << 63, -126))


class ExpansionPreparationTests(unittest.TestCase):
    """Memory, transpose, generation and alias admission."""

    def test_maximum_shape_fits_frozen_resident_and_peak_caps(self):
        receipt = candidate.layout_receipt(65_536, 65_536, 1 << 23)
        self.assertEqual(receipt["resident_bytes"], 295_960_592)
        self.assertEqual(receipt["peak_bytes"], 532_414_480)
        self.assertLessEqual(receipt["resident_bytes"], 1 << 30)
        self.assertLessEqual(receipt["peak_bytes"], 2 << 30)
        self.assertEqual(receipt["candidate_bytes_per_coefficient"]["accepted_compact_soa_payload"], 11)
        self.assertEqual(receipt["candidate_bytes_per_coefficient"]["accepted_expansion_soa_payload"], 14)
        with self.assertRaisesRegex(candidate.ArithmeticRefusal, "layout_shape_limit"):
            candidate.layout_receipt(65_537, 1, 1)
        with self.assertRaisesRegex(candidate.ArithmeticRefusal, "layout_shape_limit"):
            candidate.layout_receipt(1, 1, (1 << 23) + 1)
        with self.assertRaisesRegex(candidate.ArithmeticRefusal, "layout_negative"):
            candidate.layout_receipt(-1, 1, 1)

    def test_canonical_transpose_identity_and_source_provenance(self):
        coefficients = [0x3FF0000000000000, 0xBFD0000000000000, 1]
        direct = candidate.prepare_operator(
            2,
            2,
            coefficients,
            [0, 1, 2],
            "original_binary64",
            "symbolic_power_of_two",
        )
        transposed = candidate.prepare_operator(
            2,
            2,
            coefficients,
            [2, 0, 1],
            "rounded_scaled_binary64",
            "materialized_with_error",
        )
        self.assertEqual(direct.coefficient_sha256, transposed.coefficient_sha256)
        self.assertNotEqual(direct.generation, transposed.generation)
        self.assertNotEqual(direct.source_kind, transposed.source_kind)
        with self.assertRaisesRegex(candidate.ArithmeticRefusal, "transpose_not_permutation"):
            candidate.prepare_operator(2, 2, coefficients, [0, 0, 2], "original_binary64", "symbolic_power_of_two")

    def test_apply_refuses_stale_dimensions_generations_and_aliases(self):
        operator = candidate.prepare_operator(
            2,
            3,
            [0x3FF0000000000000],
            [0],
            "original_binary64",
            "symbolic_power_of_two",
        )
        vector = candidate.prepare_vector(3, operator, 7)
        self.assertEqual(candidate.validate_apply(operator, vector, source_generation=7), 2)
        with self.assertRaisesRegex(candidate.ArithmeticRefusal, "stale_vector_generation"):
            candidate.validate_apply(operator, vector, source_generation=8)
        with self.assertRaisesRegex(candidate.ArithmeticRefusal, "apply_alias"):
            candidate.validate_apply(operator, vector, output_aliases_input=True)
        stale = replace(vector, generation=vector.generation + 1)
        with self.assertRaisesRegex(candidate.ArithmeticRefusal, "stale_operator_generation"):
            candidate.validate_apply(operator, stale)
        wrong = replace(vector, dimension=2)
        with self.assertRaisesRegex(candidate.ArithmeticRefusal, "apply_dimension"):
            candidate.validate_apply(operator, wrong)


if __name__ == "__main__":
    unittest.main()
