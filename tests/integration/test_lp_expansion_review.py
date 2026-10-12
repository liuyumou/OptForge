"""PR 17 regressions for range, canonical input and preparation admission."""

from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))

import lp_expansion_candidate as candidate
import lp_expansion_oracle as oracle


class ExpansionRangeReviewTests(unittest.TestCase):
    def test_norm_overflow_and_finite_maximum_are_distinct(self):
        for target in (candidate.BINARY64, candidate.EXPANSION64):
            maximum = candidate.Rounded((1 << target.precision) - 1, 1024 - target.precision)
            fmt = oracle.FORMATS[target.identity]
            with self.subTest(format=target.identity):
                self.assertEqual(candidate.norm([maximum], 2, target), maximum)
                overflow = candidate.Rounded(infinity_sign=1, flags=('overflow', 'inexact'))
                self.assertEqual(candidate.norm([maximum, maximum], 2, target), overflow)
                exact_squares = 2 * oracle.exact_value(maximum.document()) ** 2
                self.assertEqual(oracle.sqrt_result(exact_squares, fmt), overflow.document())

    def test_sqrt_rounding_at_overflow_and_underflow_midpoints(self):
        for target in (candidate.BINARY64, candidate.EXPANSION64):
            fmt = oracle.FORMATS[target.identity]
            # Midpoint between the largest finite value and the next binade.
            midpoint = (1 << (target.precision + 1)) - 1
            exponent = 2 * (1023 - target.precision)
            maximum = candidate.Rounded((1 << target.precision) - 1, 1024 - target.precision)
            for delta in (-1, 0, 1):
                exact = candidate.Rounded(midpoint * midpoint + delta, exponent)
                actual = candidate.square_root(exact, target)
                expected = (replace(maximum, flags=('inexact',), error_exponent=maximum.exponent - 1)
                            if delta < 0 else candidate.Rounded(infinity_sign=1, flags=('overflow', 'inexact')))
                with self.subTest(format=target.identity, delta=delta):
                    self.assertEqual(actual, expected)
                    self.assertEqual(oracle.sqrt_result(oracle.exact_value(exact.document()), fmt), expected.document())
            tiny = candidate.Rounded(1, 2 * target.minimum_unit_exponent - 2)
            zero = candidate.Rounded(flags=('underflow', 'inexact'), error_exponent=target.minimum_unit_exponent - 1)
            self.assertEqual(candidate.square_root(tiny, target), zero)
            self.assertEqual(oracle.sqrt_result(oracle.exact_value(tiny.document()), fmt), zero.document())

    def test_small_format_against_exhaustive_representable_lattice(self):
        # Enumerating every result uses neither implementation's log/quotient
        # rounding algorithm. Include the overflowing next binade as the final
        # even tie candidate, then test every rounding boundary from both sides.
        target = candidate.BinaryFormat('review-small-format', 3, -2, 2)
        fmt = (3, -2, 2)
        lattice = [(Fraction(), candidate.Rounded())]
        for coefficient in range(1, 4):
            lattice.append((Fraction(coefficient, 16), candidate.Rounded(coefficient, -4)))
        for exponent in range(-4, 1):
            for coefficient in range(4, 8):
                value = Fraction(coefficient) * Fraction(2) ** exponent
                lattice.append((value, candidate.Rounded(coefficient, exponent)))
        lattice.append((Fraction(8), candidate.Rounded(infinity_sign=1)))
        for (low, _), (high, _) in zip(lattice, lattice[1:]):
            for offset in (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)):
                exact = low + (high - low) * offset
                _, nearest = min(lattice, key=lambda item: (abs(item[0] - exact), item[1].coefficient & 1))
                for sign in (-1, 1):
                    rounded = candidate.round_rational(sign * exact.numerator, exact.denominator, 0, target)
                    expected = replace(nearest, coefficient=sign * nearest.coefficient,
                                       infinity_sign=sign * nearest.infinity_sign,
                                       zero_sign=int(sign < 0 and nearest.coefficient == 0 and not nearest.infinity_sign))
                    self.assertEqual(rounded.plain(), expected)
                    self.assertEqual(oracle.round_fraction(sign * exact, fmt), rounded.document())
                square = exact * exact
                # The operands here are exact dyadics, including values outside
                # the output format, as in an exact sum of squares for norm2.
                source = candidate.Rounded(square.numerator, -(square.denominator.bit_length() - 1))
                root = candidate.square_root(source, target)
                self.assertEqual(root.plain(), nearest)
                self.assertEqual(oracle.sqrt_result(square, fmt), root.document())
                if nearest.infinity_sign:
                    self.assertEqual(root.flags, ('overflow', 'inexact'))
                else:
                    error = abs(Fraction(nearest.coefficient) * Fraction(2) ** nearest.exponent - exact)
                    self.assertLessEqual(error, Fraction(2) ** root.error_exponent)

    def test_fma_preserves_like_signed_zero_terms(self):
        for target in (candidate.BINARY64, candidate.EXPANSION64):
            for left_sign in (0, 1):
                for right_sign in (0, 1):
                    for addend_sign in (0, 1):
                        operands = [candidate.Rounded(zero_sign=left_sign),
                                    candidate.Rounded(-1 if right_sign else 1),
                                    candidate.Rounded(zero_sign=addend_sign)]
                        expected = candidate.Rounded(zero_sign=(left_sign ^ right_sign) & addend_sign)
                        with self.subTest(format=target.identity, signs=(left_sign, right_sign, addend_sign)):
                            self.assertEqual(candidate.fused_multiply_add(*operands, target), expected)
                            self.assertEqual(oracle.primitive_result('fma', [x.document() for x in operands], oracle.FORMATS[target.identity]), expected.document())
            self.assertEqual(candidate.fused_multiply_add(candidate.Rounded(-1), candidate.Rounded(1), candidate.Rounded(1), target), candidate.Rounded())

    def test_projection_rejects_nonfinite_values_and_bounds_before_branches(self):
        for bad in (candidate.Rounded(infinity_sign=1), candidate.Rounded(infinity_sign=-1), candidate.Rounded(invalid=True)):
            for value, lower, upper in ((bad, None, None), (bad, None, candidate.Rounded(1)),
                                        (candidate.Rounded(), bad, None), (candidate.Rounded(), None, bad)):
                with self.subTest(value=value, lower=lower, upper=upper):
                    with self.assertRaises(candidate.ArithmeticRefusal):
                        candidate.project(value, lower, upper)


class ExpansionCodecReviewTests(unittest.TestCase):
    def test_binary64_inputs_must_be_unsigned_64_bit_integers(self):
        for bits in (-1, 1 << 64, (1 << 64) | 0x3FF0000000000000, True, 1.0, '1'):
            for operation in (candidate.encode_binary64, candidate.binary64_bits_to_dyadic):
                with self.subTest(bits=bits, operation=operation.__name__):
                    with self.assertRaises(candidate.ArithmeticRefusal):
                        operation(bits)

    def test_codec_fields_refuse_noninteger_aliases(self):
        valid = candidate.encode_binary64(0x3FF0000000000000)
        for field, value in (('tail', 0.0), ('tail', False), ('exponent', 1.0),
                             ('zero_sign', False), ('high_bits', 1 << 32), ('low_bits', -1)):
            with self.subTest(field=field, value=value):
                with self.assertRaises(candidate.ArithmeticRefusal):
                    candidate.decode_binary64(replace(valid, **{field: value}))

    def test_expansion_encoder_refuses_values_outside_its_format(self):
        for value in (candidate.Rounded(1 << 63, 961), candidate.Rounded(1 << 63, -1086),
                      candidate.Rounded(zero_sign=2), candidate.Rounded(zero_sign=False)):
            with self.subTest(value=value):
                with self.assertRaises(candidate.ArithmeticRefusal):
                    candidate.expansion_chunks(value)
        for value in (candidate.Rounded(1, -1085), candidate.Rounded((1 << 64) - 1, 960), candidate.Rounded(zero_sign=1)):
            self.assertEqual(candidate.decode_expansion_chunks(candidate.expansion_chunks(value)), value)

    def test_expansion_documents_refuse_malformed_structure_and_fields(self):
        valid = candidate.expansion_chunks(candidate.Rounded(1 << 63, -63))
        malformed = [None, {}, dict(valid, extra=0), dict(valid, sign=False),
                     dict(valid, sign=0.0), dict(valid, exponent=1.0),
                     dict(valid, chunks=[8388608.0, 0, 0]),
                     dict(valid, chunks=[8388608, False, 0]), dict(valid, chunks=None),
                     dict(valid, exponent=1025), dict(valid, exponent=-1022)]
        for document in malformed:
            with self.subTest(document=document):
                with self.assertRaises(candidate.ArithmeticRefusal):
                    candidate.decode_expansion_chunks(document)


class ExpansionPreparationReviewTests(unittest.TestCase):
    @staticmethod
    def operator(rows=2, columns=2, transpose=(0, 1)):
        return candidate.prepare_operator(rows, columns, [0x3FF0000000000000, 1], list(transpose), 'original_binary64', 'symbolic_power_of_two')

    def test_generation_binds_shape_and_transpose_map(self):
        original = self.operator()
        vector = candidate.prepare_vector(2, original, 7)
        self.assertEqual(self.operator().generation, original.generation)
        for other in (self.operator(rows=3), self.operator(columns=3), self.operator(transpose=(1, 0))):
            with self.subTest(other=other):
                self.assertNotEqual(other.generation, original.generation)
                with self.assertRaises(candidate.ArithmeticRefusal):
                    candidate.validate_apply(other, vector, source_generation=7)

    def test_shape_and_memory_admission_precede_coefficient_or_map_work(self):
        class Untouched:
            def __len__(self):
                return 2

            def __iter__(self):
                raise AssertionError('admission must precede traversal')

        with self.assertRaisesRegex(candidate.ArithmeticRefusal, 'layout_shape_limit'):
            candidate.prepare_operator(65537, 2, Untouched(), Untouched(), 'original_binary64', 'symbolic_power_of_two')
        for rows, columns in ((0, 2), (2, 0), (1, 1)):
            with self.assertRaisesRegex(candidate.ArithmeticRefusal, 'layout_nonzero_shape'):
                candidate.prepare_operator(rows, columns, Untouched(), Untouched(), 'original_binary64', 'symbolic_power_of_two')
        for cap in ('RESIDENT_CAP', 'PEAK_CAP'):
            with patch.object(candidate, cap, 0):
                with self.assertRaisesRegex(candidate.ArithmeticRefusal, 'layout_.*_cap'):
                    candidate.prepare_operator(2, 2, Untouched(), Untouched(), 'original_binary64', 'symbolic_power_of_two')

    def test_receipt_integer_fields_are_strict(self):
        for shape in ((True, 2, 2), (2.0, 2, 2), (2, 2, False)):
            with self.assertRaises(candidate.ArithmeticRefusal):
                candidate.layout_receipt(*shape)
        for mapping in ([False, 1], [0, 1.0]):
            with self.assertRaises(candidate.ArithmeticRefusal):
                self.operator(transpose=mapping)
        for generation in (-1, False, 0.0):
            with self.assertRaises(candidate.ArithmeticRefusal):
                candidate.prepare_vector(2, self.operator(), generation)
        with self.assertRaisesRegex(candidate.ArithmeticRefusal, 'layout_integer_overflow'):
            candidate._checked_sum(candidate.U64_MAX, 1)

    def test_apply_cannot_omit_current_vector_epoch(self):
        operator = self.operator()
        vector = candidate.prepare_vector(2, operator, 7)
        with self.assertRaises((candidate.ArithmeticRefusal, TypeError)):
            candidate.validate_apply(operator, vector)
        for generation in (None, False, 7.0, 8):
            with self.assertRaises(candidate.ArithmeticRefusal):
                candidate.validate_apply(operator, vector, source_generation=generation)
        self.assertEqual(candidate.validate_apply(operator, vector, source_generation=7), 2)


if __name__ == '__main__':
    unittest.main()
