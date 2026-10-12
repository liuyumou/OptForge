"""Integer-only GPUP-REP candidate arithmetic and preparation contracts.

This module deliberately does not import ``fractions`` or use host floating-point
arithmetic.  ``tools/lp_expansion_oracle.py`` is the independent exact-rational
authority used by the acceptance tests.
"""

from dataclasses import asdict, dataclass
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct


U64_MAX = (1 << 64) - 1
MAX_ROWS = 65_536
MAX_COLUMNS = 65_536
MAX_NONZEROS = 1 << 23
RESIDENT_CAP = 1 << 30
PEAK_CAP = 2 << 30


class ArithmeticRefusal(ValueError):
    """A named arithmetic or preparation contract refusal."""


@dataclass(frozen=True)
class BinaryFormat:
    """A finite binary format with gradual underflow."""

    identity: str
    precision: int
    minimum_normal_exponent: int
    maximum_exponent: int

    @property
    def minimum_unit_exponent(self):
        """Exponent of the least positive subnormal."""
        return self.minimum_normal_exponent - (self.precision - 1)


BINARY32 = BinaryFormat("ieee-binary32-rne-v1", 24, -126, 127)
BINARY64 = BinaryFormat("ieee-binary64-rne-v1", 53, -1022, 1023)
EXPANSION64 = BinaryFormat("fp32-24-24-16-expansion-rne-v1", 64, -1022, 1023)


@dataclass(frozen=True)
class Rounded:
    """A rounded number: coefficient times two to exponent."""

    coefficient: int = 0
    exponent: int = 0
    zero_sign: int = 0
    infinity_sign: int = 0
    invalid: bool = False
    flags: tuple[str, ...] = ()
    error_exponent: int | None = None

    def plain(self):
        """Drop operation diagnostics when reusing a result as an operand."""
        return Rounded(
            coefficient=self.coefficient,
            exponent=self.exponent,
            zero_sign=self.zero_sign,
            infinity_sign=self.infinity_sign,
            invalid=self.invalid,
        )

    def document(self):
        """Canonical JSON-compatible representation."""
        value = asdict(self)
        value["flags"] = list(self.flags)
        return value


@dataclass(frozen=True)
class CodecTuple:
    """Canonical exact binary64 input codec."""

    high_bits: int
    low_bits: int
    tail: int
    exponent: int
    zero_sign: int = 0

    def document(self):
        """Canonical JSON-compatible representation."""
        return {
            "high_bits": f"{self.high_bits:08x}",
            "low_bits": f"{self.low_bits:08x}",
            "tail": self.tail,
            "exponent": self.exponent,
            "zero_sign": self.zero_sign,
        }


def _require(condition, message):
    if not condition:
        raise ArithmeticRefusal(message)


def _floor_log2_rational(numerator, denominator):
    """Return floor(log2(numerator / denominator)) using integers only."""
    _require(numerator > 0 and denominator > 0, "log2_domain")
    exponent = numerator.bit_length() - denominator.bit_length()
    if exponent >= 0:
        if numerator < denominator << exponent:
            exponent -= 1
    elif numerator << -exponent < denominator:
        exponent -= 1
    return exponent


def _scaled_divmod(numerator, denominator, shift):
    if shift >= 0:
        return divmod(numerator << shift, denominator)
    return divmod(numerator, denominator << -shift)


def _round_quotient(numerator, denominator, shift):
    quotient, remainder = _scaled_divmod(numerator, denominator, shift)
    divisor = denominator if shift >= 0 else denominator << -shift
    twice = remainder << 1
    increment = twice > divisor or (twice == divisor and quotient & 1)
    return quotient + int(increment), remainder == 0, increment


def round_rational(
    numerator,
    denominator,
    binary_exponent,
    target,
    *,
    zero_sign=0,
):
    """Round ``numerator / denominator * 2**binary_exponent`` to target."""
    _require(denominator > 0, "denominator")
    if numerator == 0:
        return Rounded(zero_sign=zero_sign)
    sign = -1 if numerator < 0 else 1
    numerator = abs(numerator)
    exact_exponent = _floor_log2_rational(numerator, denominator) + binary_exponent
    unit_exponent = max(
        exact_exponent - (target.precision - 1), target.minimum_unit_exponent
    )
    quotient, exact, _ = _round_quotient(
        numerator, denominator, binary_exponent - unit_exponent
    )
    if quotient >= 1 << target.precision:
        quotient >>= 1
        unit_exponent += 1
        exact_exponent += 1
    if exact_exponent > target.maximum_exponent or (
        exact_exponent == target.maximum_exponent
        and quotient >= 1 << target.precision
    ):
        return Rounded(
            infinity_sign=sign,
            flags=("overflow", "inexact"),
        )
    if quotient == 0:
        flags = ("underflow", "inexact")
        return Rounded(zero_sign=int(sign < 0), flags=flags, error_exponent=unit_exponent - 1)
    inexact = not exact
    subnormal = quotient < 1 << (target.precision - 1)
    flags = []
    if subnormal and inexact:
        flags.append("underflow")
    if inexact:
        flags.append("inexact")
    return Rounded(
        coefficient=sign * quotient,
        exponent=unit_exponent,
        flags=tuple(flags),
        error_exponent=unit_exponent - 1 if inexact else None,
    )


def _align(left_coefficient, left_exponent, right_coefficient, right_exponent):
    exponent = min(left_exponent, right_exponent)
    left = left_coefficient << (left_exponent - exponent)
    right = right_coefficient << (right_exponent - exponent)
    return left, right, exponent


def _finite_operand(value):
    _require(not value.invalid, "invalid_operand")
    _require(value.infinity_sign == 0, "nonfinite_operand")
    return value.coefficient, value.exponent


def normalize(value, target):
    """Normalize and round one represented finite value to ``target``."""
    coefficient, exponent = _finite_operand(value)
    return round_rational(
        coefficient, 1, exponent, target, zero_sign=value.zero_sign
    )


def negate(value):
    """Exact negation with signed-zero preservation."""
    coefficient, exponent = _finite_operand(value)
    if coefficient == 0:
        return Rounded(zero_sign=1 - value.zero_sign)
    return Rounded(coefficient=-coefficient, exponent=exponent)


def absolute(value):
    """Exact absolute value."""
    coefficient, exponent = _finite_operand(value)
    return Rounded(coefficient=abs(coefficient), exponent=exponent)


def add(left, right, target, *, subtract=False):
    """Correctly round one exact addition or subtraction."""
    a, ae = _finite_operand(left)
    b, be = _finite_operand(right)
    if subtract:
        b = -b
    a, b, exponent = _align(a, ae, b, be)
    zero_sign = int(a + b == 0 and left.zero_sign and (right.zero_sign ^ subtract))
    return round_rational(a + b, 1, exponent, target, zero_sign=zero_sign)


def multiply(left, right, target):
    """Correctly round one exact product."""
    a, ae = _finite_operand(left)
    b, be = _finite_operand(right)
    left_sign = int(a < 0) if a else left.zero_sign
    right_sign = int(b < 0) if b else right.zero_sign
    zero_sign = left_sign ^ right_sign
    return round_rational(a * b, 1, ae + be, target, zero_sign=zero_sign)


def fused_multiply_add(left, right, addend, target):
    """Round once after an exact product and addition."""
    a, ae = _finite_operand(left)
    b, be = _finite_operand(right)
    c, ce = _finite_operand(addend)
    product_exponent = ae + be
    product, c, exponent = _align(a * b, product_exponent, c, ce)
    return round_rational(product + c, 1, exponent, target)


def divide(left, right, target):
    """Correctly round one quotient through quotient/remainder decisions."""
    a, ae = _finite_operand(left)
    b, be = _finite_operand(right)
    if b == 0:
        if a == 0:
            return Rounded(invalid=True, flags=("invalid",))
        sign = -1 if (a < 0) ^ bool(right.zero_sign) else 1
        return Rounded(infinity_sign=sign, flags=("divide_by_zero",))
    if a == 0:
        return Rounded(zero_sign=left.zero_sign ^ int(b < 0))
    sign = -1 if (a < 0) ^ (b < 0) else 1
    return round_rational(sign * abs(a), abs(b), ae - be, target)


def square_root(value, target):
    """Correctly round a square root using integer roots and midpoint squares."""
    coefficient, exponent = _finite_operand(value)
    if coefficient < 0:
        return Rounded(invalid=True, flags=("invalid",))
    if coefficient == 0:
        return Rounded(zero_sign=value.zero_sign)
    source_exponent = _floor_log2_rational(coefficient, 1) + exponent
    result_exponent = source_exponent // 2
    unit_exponent = max(
        result_exponent - (target.precision - 1), target.minimum_unit_exponent
    )
    shift = exponent - 2 * unit_exponent
    if shift >= 0:
        numerator, denominator = coefficient << shift, 1
    else:
        numerator, denominator = coefficient, 1 << -shift
    # floor(sqrt(numerator / denominator)) is sqrt(floor(...)) rounded down.
    quotient = math.isqrt(numerator // denominator)
    midpoint = 2 * quotient + 1
    comparison = 4 * numerator - denominator * midpoint * midpoint
    if comparison > 0 or (comparison == 0 and quotient & 1):
        quotient += 1
    exact = denominator * quotient * quotient == numerator
    if quotient >= 1 << target.precision:
        quotient >>= 1
        unit_exponent += 1
    flags = () if exact else ("inexact",)
    subnormal = quotient < 1 << (target.precision - 1)
    if subnormal and not exact:
        flags = ("underflow", "inexact")
    return Rounded(
        coefficient=quotient,
        exponent=unit_exponent,
        flags=flags,
        error_exponent=unit_exponent - 1 if not exact else None,
    )


def compare(left, right):
    """Compare exact represented finite values."""
    a, ae = _finite_operand(left)
    b, be = _finite_operand(right)
    a, b, _ = _align(a, ae, b, be)
    return (a > b) - (a < b)


def exact_sum(values):
    """Accumulate represented dyadics exactly in one exponent bin."""
    if not values:
        return 0, 0
    operands = [_finite_operand(value) for value in values]
    exponent = min(item[1] for item in operands)
    coefficient = sum(value << (item_exponent - exponent) for value, item_exponent in operands)
    return coefficient, exponent


def reduce_sum(values, target):
    """Round once after an exact represented sum."""
    coefficient, exponent = exact_sum(values)
    return round_rational(coefficient, 1, exponent, target)


def dot(left, right, target):
    """Round once after an exact represented dot product."""
    _require(len(left) == len(right), "dimension")
    products = []
    for a, b in zip(left, right):
        ac, ae = _finite_operand(a)
        bc, be = _finite_operand(b)
        products.append(Rounded(coefficient=ac * bc, exponent=ae + be))
    return reduce_sum(products, target)


def norm(values, kind, target):
    """Correctly rounded 1, 2 or infinity norm."""
    _require(kind in (1, 2, "inf"), "norm_kind")
    if kind == "inf":
        if not values:
            return Rounded()
        maximum = Rounded()
        for value in values:
            candidate = absolute(value)
            if compare(candidate, maximum) > 0:
                maximum = candidate
        return maximum
    if kind == 1:
        return reduce_sum([absolute(value) for value in values], target)
    squares = []
    for value in values:
        coefficient, exponent = _finite_operand(value)
        squares.append(Rounded(coefficient=coefficient * coefficient, exponent=2 * exponent))
    exact_coefficient, exact_exponent = exact_sum(squares)
    return square_root(Rounded(coefficient=exact_coefficient, exponent=exact_exponent), target)


def project(value, lower, upper):
    """Project onto a tagged interval; ``None`` denotes an infinite bound."""
    if lower is not None and upper is not None:
        _require(compare(lower, upper) <= 0, "invalid_bounds")
    if lower is not None and compare(value, lower) < 0:
        return lower.plain()
    if upper is not None and compare(value, upper) > 0:
        return upper.plain()
    return value.plain()


def binary64_bits_to_dyadic(bits):
    """Decode finite IEEE binary64 bits with integer operations."""
    sign = -1 if bits >> 63 else 1
    exponent_field = bits >> 52 & 0x7FF
    fraction = bits & ((1 << 52) - 1)
    _require(exponent_field != 0x7FF, "nonfinite_input")
    if exponent_field == 0:
        if fraction == 0:
            return Rounded(zero_sign=int(sign < 0))
        return Rounded(coefficient=sign * fraction, exponent=-1074)
    return Rounded(
        coefficient=sign * ((1 << 52) | fraction),
        exponent=exponent_field - 1023 - 52,
    )


def round_binary64_bits(bits, target):
    """Convert a finite binary64 input directly to a target format."""
    value = binary64_bits_to_dyadic(bits)
    return round_rational(
        value.coefficient,
        1,
        value.exponent,
        target,
        zero_sign=value.zero_sign,
    )


def rounded_to_binary64_bits(value):
    """Encode an exactly representable finite Rounded value as binary64 bits."""
    _require(not value.invalid and not value.infinity_sign, "nonfinite_result")
    if value.coefficient == 0:
        return value.zero_sign << 63
    sign_bit = int(value.coefficient < 0) << 63
    magnitude = abs(value.coefficient)
    lowest = (magnitude & -magnitude).bit_length() - 1
    magnitude >>= lowest
    exponent = value.exponent + lowest
    top = magnitude.bit_length() - 1 + exponent
    _require(-1074 <= top <= 1023, "binary64_range")
    if top < -1022:
        shift = exponent + 1074
        _require(shift >= 0, "binary64_subnormal_canonical")
        fraction = magnitude << shift
        _require(fraction < 1 << 52, "binary64_subnormal_width")
        return sign_bit | fraction
    shift = 52 - (magnitude.bit_length() - 1)
    _require(shift >= 0, "binary64_inexact")
    significand = magnitude << shift
    exponent_field = top + 1023
    return sign_bit | (exponent_field << 52) | (significand & ((1 << 52) - 1))


def _f32_bits_to_dyadic(bits):
    sign = -1 if bits >> 31 else 1
    exponent_field = bits >> 23 & 0xFF
    fraction = bits & ((1 << 23) - 1)
    _require(exponent_field != 0xFF, "codec_nonfinite_component")
    if exponent_field == 0:
        if fraction == 0:
            return Rounded(zero_sign=int(sign < 0))
        return Rounded(coefficient=sign * fraction, exponent=-149)
    return Rounded(
        coefficient=sign * ((1 << 23) | fraction),
        exponent=exponent_field - 127 - 23,
    )


def _dyadic_to_f32_bits(value):
    _require(not value.flags and not value.infinity_sign and not value.invalid, "codec_component")
    if value.coefficient == 0:
        return value.zero_sign << 31
    sign_bit = int(value.coefficient < 0) << 31
    magnitude = abs(value.coefficient)
    lowest = (magnitude & -magnitude).bit_length() - 1
    magnitude >>= lowest
    exponent = value.exponent + lowest
    top = magnitude.bit_length() - 1 + exponent
    if top < -126:
        shift = exponent + 149
        _require(shift >= 0, "codec_f32_subnormal")
        fraction = magnitude << shift
        _require(fraction < 1 << 23, "codec_f32_subnormal")
        return sign_bit | fraction
    shift = 23 - (magnitude.bit_length() - 1)
    _require(shift >= 0, "codec_f32_width")
    significand = magnitude << shift
    return sign_bit | ((top + 127) << 23) | (significand & ((1 << 23) - 1))


def _codec_normalized(bits):
    sign = -1 if bits >> 63 else 1
    exponent_field = bits >> 52 & 0x7FF
    fraction = bits & ((1 << 52) - 1)
    _require(exponent_field != 0x7FF, "nonfinite_input")
    if exponent_field == 0:
        if fraction == 0:
            return 0, 0, int(sign < 0)
        shift = 53 - fraction.bit_length()
        return sign * (fraction << shift), -1021 - shift, 0
    return sign * ((1 << 52) | fraction), exponent_field - 1022, 0


def encode_binary64(bits):
    """Encode finite binary64 bits as canonical h/l/q plus symbolic exponent."""
    mantissa, exponent, zero_sign = _codec_normalized(bits)
    if mantissa == 0:
        return CodecTuple(zero_sign=zero_sign, high_bits=zero_sign << 31, low_bits=0, tail=0, exponent=0)
    high = round_rational(mantissa, 1, -53, BINARY32)
    high_coefficient, high_exponent = high.coefficient, high.exponent
    mantissa_on_lattice = mantissa
    high_shift = high_exponent + 53
    high_on_lattice = high_coefficient << high_shift
    residual = mantissa_on_lattice - high_on_lattice
    low = round_rational(residual, 1, -53, BINARY32)
    low_shift = low.exponent + 53
    if low_shift >= 0:
        low_on_lattice = low.coefficient << low_shift
    else:
        divisor = 1 << -low_shift
        _require(low.coefficient % divisor == 0, "codec_low_lattice")
        low_on_lattice = low.coefficient // divisor
    tail = residual - low_on_lattice
    _require(-8 <= tail <= 8, "codec_tail_range")
    return CodecTuple(
        high_bits=_dyadic_to_f32_bits(high.plain()),
        low_bits=_dyadic_to_f32_bits(low.plain()),
        tail=tail,
        exponent=exponent,
    )


def decode_binary64(codec):
    """Decode and validate a canonical tuple, returning original binary64 bits."""
    _require(-8 <= codec.tail <= 8, "codec_tail_range")
    _require(-1073 <= codec.exponent <= 1024, "codec_exponent_range")
    _require(codec.zero_sign in (0, 1), "codec_zero_sign")
    high = _f32_bits_to_dyadic(codec.high_bits)
    low = _f32_bits_to_dyadic(codec.low_bits)
    if high.coefficient == 0:
        _require(
            codec.low_bits == 0 and codec.tail == 0 and codec.exponent == 0,
            "codec_noncanonical_zero",
        )
        _require(high.zero_sign == codec.zero_sign, "codec_zero_sign")
        bits = codec.zero_sign << 63
    else:
        _require(codec.zero_sign == 0, "codec_nonzero_zero_tag")
        values = [
            Rounded(high.coefficient, high.exponent + codec.exponent),
            Rounded(low.coefficient, low.exponent + codec.exponent),
            Rounded(codec.tail, codec.exponent - 53),
        ]
        coefficient, exponent = exact_sum(values)
        rounded = round_rational(coefficient, 1, exponent, BINARY64)
        _require(not rounded.flags, "codec_not_exact_binary64")
        bits = rounded_to_binary64_bits(rounded)
    _require(encode_binary64(bits) == codec, "codec_noncanonical")
    return bits


def expansion_chunks(value):
    """Encode a canonical finite expansion value as 24/24/16 FP32 chunks."""
    _require(not value.invalid and not value.infinity_sign, "expansion_nonfinite")
    if value.coefficient == 0:
        return {"sign": value.zero_sign, "chunks": [0, 0, 0], "exponent": 0}
    magnitude = abs(value.coefficient)
    _require(magnitude < 1 << 64, "expansion_significand_width")
    _require(
        value.exponent == EXPANSION64.minimum_unit_exponent
        or magnitude >= 1 << (EXPANSION64.precision - 1),
        "expansion_noncanonical_significand",
    )
    chunks = [magnitude >> 40, magnitude >> 16 & 0xFFFFFF, magnitude & 0xFFFF]
    return {
        "sign": int(value.coefficient < 0),
        "chunks": chunks,
        "exponent": value.exponent + 64,
    }


def decode_expansion_chunks(document):
    """Validate and decode canonical positional chunks."""
    _require(document["sign"] in (0, 1), "expansion_sign")
    chunks = document["chunks"]
    _require(len(chunks) == 3, "expansion_chunk_count")
    _require(0 <= chunks[0] < 1 << 24, "expansion_chunk0")
    _require(0 <= chunks[1] < 1 << 24, "expansion_chunk1")
    _require(0 <= chunks[2] < 1 << 16, "expansion_chunk2")
    magnitude = chunks[0] << 40 | chunks[1] << 16 | chunks[2]
    if magnitude == 0:
        _require(document["exponent"] == 0, "expansion_noncanonical_zero")
        return Rounded(zero_sign=document["sign"])
    value = Rounded(
        coefficient=(-1 if document["sign"] else 1) * magnitude,
        exponent=document["exponent"] - 64,
    )
    _require(
        value.exponent == EXPANSION64.minimum_unit_exponent
        or magnitude >= 1 << (EXPANSION64.precision - 1),
        "expansion_noncanonical_significand",
    )
    _require(expansion_chunks(value) == document, "expansion_noncanonical")
    _require(-1085 <= value.exponent, "expansion_exponent_range")
    _require(value.coefficient.bit_length() + value.exponent - 1 <= 1023, "expansion_exponent_range")
    return value


def _checked_sum(*values):
    total = 0
    for value in values:
        _require(isinstance(value, int) and value >= 0, "layout_negative")
        _require(value <= U64_MAX - total, "layout_integer_overflow")
        total += value
    return total


def layout_receipt(rows, columns, nonzeros):
    """Return checked resident/peak bytes for the accepted bounded layout."""
    _require(rows <= MAX_ROWS and columns <= MAX_COLUMNS and nonzeros <= MAX_NONZEROS, "layout_shape_limit")
    _require(rows >= 0 and columns >= 0 and nonzeros >= 0, "layout_negative")
    offsets = _checked_sum((rows + 1) * 8, (columns + 1) * 8)
    sparse_maps = _checked_sum(nonzeros * 4, nonzeros * 4, offsets)
    compact = _checked_sum(nonzeros * 11, (nonzeros + 7) // 8)
    decoded = nonzeros * 14
    live_vectors = _checked_sum((rows + columns) * 14 * 5, (rows + columns) * 8 * 4)
    checkpoints = (rows + columns) * 14 * 2
    accumulator_scratch = max(rows, columns) * 67 * 8
    resident = _checked_sum(compact, decoded, sparse_maps, live_vectors, checkpoints)
    peak = _checked_sum(resident, nonzeros * 8, nonzeros * 16, accumulator_scratch)
    _require(resident <= RESIDENT_CAP, "layout_resident_cap")
    _require(peak <= PEAK_CAP, "layout_peak_cap")
    return {
        "identity": "lp-expansion-layout-v1",
        "rows": rows,
        "columns": columns,
        "nonzeros": nonzeros,
        "candidate_bytes_per_coefficient": {
            "original_binary64_bits": 8,
            "two_fp32_scaled_fp16_i16_aligned": 12,
            "two_fp32_bf16_i16_aligned": 12,
            "two_fp32_int8_i16_separate_payload": 11,
            "accepted_compact_soa_payload": 11,
            "accepted_expansion_soa_payload": 14,
            "existing_parts3_i32_abi": 16,
        },
        "compact_operator_bytes": compact,
        "decoded_operator_bytes": decoded,
        "sparse_map_bytes": sparse_maps,
        "live_vector_bytes": live_vectors,
        "checkpoint_bytes": checkpoints,
        "accumulator_scratch_bytes": accumulator_scratch,
        "resident_bytes": resident,
        "peak_bytes": peak,
        "resident_cap_bytes": RESIDENT_CAP,
        "peak_cap_bytes": PEAK_CAP,
    }


@dataclass(frozen=True)
class PreparedOperator:
    """CPU validation receipt for one canonical operator and transpose map."""

    identity: str
    rows: int
    columns: int
    nonzeros: int
    coefficient_sha256: str
    source_kind: str
    scale_policy: str
    generation: int
    layout: dict


@dataclass(frozen=True)
class PreparedVector:
    """A dimension- and generation-bound decoded vector receipt."""

    dimension: int
    generation: int
    source_generation: int


def prepare_operator(rows, columns, coefficient_bits, transpose_map, source_kind, scale_policy):
    """Validate canonical coefficients and a permutation-only transpose."""
    _require(source_kind in ("original_binary64", "rounded_scaled_binary64"), "source_kind")
    _require(scale_policy in ("symbolic_power_of_two", "materialized_with_error"), "scale_policy")
    nonzeros = len(coefficient_bits)
    _require(len(transpose_map) == nonzeros, "transpose_dimension")
    _require(sorted(transpose_map) == list(range(nonzeros)), "transpose_not_permutation")
    for bits in coefficient_bits:
        decode_binary64(encode_binary64(bits))
    payload = b"".join(struct.pack(">Q", bits) for bits in coefficient_bits)
    digest = hashlib.sha256(payload).hexdigest()
    generation = int.from_bytes(
        hashlib.sha256(payload + source_kind.encode() + scale_policy.encode()).digest()[:8],
        "big",
    )
    return PreparedOperator(
        identity="lp-expansion-operator-v1",
        rows=rows,
        columns=columns,
        nonzeros=nonzeros,
        coefficient_sha256=digest,
        source_kind=source_kind,
        scale_policy=scale_policy,
        generation=generation,
        layout=layout_receipt(rows, columns, nonzeros),
    )


def prepare_vector(dimension, operator, source_generation):
    """Bind one decoded vector to an operator and source epoch."""
    _require(dimension in (operator.rows, operator.columns), "vector_dimension")
    _require(source_generation >= 0, "vector_source_generation")
    return PreparedVector(dimension, operator.generation, source_generation)


def validate_apply(
    operator,
    vector,
    *,
    transpose=False,
    output_aliases_input=False,
    source_generation=None,
):
    """Validate generation, dimension and alias rules before an apply."""
    expected = operator.rows if transpose else operator.columns
    _require(vector.dimension == expected, "apply_dimension")
    _require(vector.generation == operator.generation, "stale_operator_generation")
    if source_generation is not None:
        _require(vector.source_generation == source_generation, "stale_vector_generation")
    _require(not output_aliases_input, "apply_alias")
    return operator.columns if transpose else operator.rows


def load_rounded(document):
    """Load an oracle fixture operand without sharing oracle arithmetic."""
    return Rounded(
        coefficient=int(document.get("coefficient", 0)),
        exponent=int(document.get("exponent", 0)),
        zero_sign=int(document.get("zero_sign", 0)),
    )


def verify_fixture(path):
    """Verify an independently generated GPUP-REP fixture."""
    document = json.loads(Path(path).read_text())
    _require(document["schema"] == "lp-expansion-oracle-v1", "fixture_schema")
    formats = {BINARY64.identity: BINARY64, EXPANSION64.identity: EXPANSION64}
    for case in document["codec_cases"]:
        bits = int(case["bits"], 16)
        codec = encode_binary64(bits)
        _require(codec.document() == case["codec"], "fixture_codec")
        _require(decode_binary64(codec) == bits, "fixture_codec_roundtrip")
    for case in document["primitive_cases"]:
        target = formats[case["format"]]
        operands = [load_rounded(item) for item in case["operands"]]
        operation = case["operation"]
        if operation == "convert":
            result = normalize(operands[0], target)
        elif operation == "negate":
            result = negate(operands[0])
        elif operation == "abs":
            result = absolute(operands[0])
        elif operation == "add":
            result = add(operands[0], operands[1], target)
        elif operation == "subtract":
            result = add(operands[0], operands[1], target, subtract=True)
        elif operation == "multiply":
            result = multiply(operands[0], operands[1], target)
        elif operation == "fma":
            result = fused_multiply_add(*operands, target)
        elif operation == "divide":
            result = divide(operands[0], operands[1], target)
        elif operation == "sqrt":
            result = square_root(operands[0], target)
        else:
            raise ArithmeticRefusal("fixture_operation")
        _require(result.document() == case["result"], f"fixture_{operation}")
    for case in document["reduction_cases"]:
        target = formats[case["format"]]
        repeat = case.get("repeat", 1)
        left = [load_rounded(item) for item in case["left"]] * repeat
        right = [load_rounded(item) for item in case.get("right", [])] * repeat
        operation = case["operation"]
        if operation == "sum":
            result = reduce_sum(left, target)
        elif operation == "dot":
            result = dot(left, right, target)
        else:
            result = norm(left, case["kind"], target)
        _require(result.document() == case["result"], f"fixture_{operation}")
    for case in document["comparison_cases"]:
        result = compare(load_rounded(case["left"]), load_rounded(case["right"]))
        _require(result == case["result"], "fixture_compare")
    for case in document["projection_cases"]:
        lower = load_rounded(case["lower"]) if case["lower"] is not None else None
        upper = load_rounded(case["upper"]) if case["upper"] is not None else None
        result = project(load_rounded(case["value"]), lower, upper)
        _require(result == load_rounded(case["result"]), "fixture_project")
    return {
        "codec_cases": len(document["codec_cases"]),
        "primitive_cases": len(document["primitive_cases"]),
        "reduction_cases": len(document["reduction_cases"]),
        "comparison_cases": len(document["comparison_cases"]),
        "projection_cases": len(document["projection_cases"]),
        "seed": document["seed"],
    }


def main():
    """Verify the committed oracle and print bounded layout receipts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "tests/regression/lp-expansion-oracle-v1.json",
    )
    parser.add_argument(
        "--layout",
        nargs=3,
        metavar=("ROWS", "COLUMNS", "NONZEROS"),
        type=int,
    )
    args = parser.parse_args()
    report = {"oracle": verify_fixture(args.fixture)}
    if args.layout:
        report["layout"] = layout_receipt(*args.layout)
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
