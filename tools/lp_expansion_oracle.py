"""Independent exact-rational GPUP-REP oracle and fixture generator.

The production candidate is integer-only and lives in ``lp_expansion_candidate``.
This module intentionally shares no rounding, codec, arithmetic or layout helpers
with it.
"""

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import random
import struct


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/regression/lp-expansion-oracle-v1.json"
SEED = 17004
FORMATS = {
    "ieee-binary64-rne-v1": (53, -1022, 1023),
    "fp32-24-24-16-expansion-rne-v1": (64, -1022, 1023),
}
FP32 = (24, -126, 127)


def power2(exponent):
    """Return an exact power of two."""
    return Fraction(1 << exponent) if exponent >= 0 else Fraction(1, 1 << -exponent)


def floor_log2(value):
    """Independent exact floor(log2(value))."""
    assert value > 0
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if value < power2(exponent):
        exponent -= 1
    return exponent


def round_integer(value):
    """Nearest-even integer rounding of a nonnegative Fraction."""
    quotient, remainder = divmod(value.numerator, value.denominator)
    if 2 * remainder > value.denominator or (
        2 * remainder == value.denominator and quotient & 1
    ):
        quotient += 1
    return quotient, remainder == 0


def result_document(
    coefficient=0,
    exponent=0,
    *,
    zero_sign=0,
    infinity_sign=0,
    invalid=False,
    flags=(),
    error_exponent=None,
):
    """Create a candidate-compatible result document."""
    return {
        "coefficient": coefficient,
        "exponent": exponent,
        "zero_sign": zero_sign,
        "infinity_sign": infinity_sign,
        "invalid": invalid,
        "flags": list(flags),
        "error_exponent": error_exponent,
    }


def round_fraction(value, format_tuple, *, zero_sign=0):
    """Round a Fraction directly to a finite binary format."""
    precision, minimum_normal, maximum = format_tuple
    minimum_unit = minimum_normal - (precision - 1)
    if value == 0:
        return result_document(zero_sign=zero_sign)
    sign = -1 if value < 0 else 1
    magnitude = abs(value)
    exact_exponent = floor_log2(magnitude)
    unit_exponent = max(exact_exponent - (precision - 1), minimum_unit)
    quotient, exact = round_integer(magnitude / power2(unit_exponent))
    if quotient >= 1 << precision:
        quotient >>= 1
        unit_exponent += 1
        exact_exponent += 1
    if exact_exponent > maximum:
        return result_document(
            infinity_sign=sign, flags=("overflow", "inexact")
        )
    if quotient == 0:
        return result_document(
            zero_sign=int(sign < 0),
            flags=("underflow", "inexact"),
            error_exponent=unit_exponent - 1,
        )
    inexact = not exact
    flags = []
    if quotient < 1 << (precision - 1) and inexact:
        flags.append("underflow")
    if inexact:
        flags.append("inexact")
    document = result_document(
        coefficient=sign * quotient,
        exponent=unit_exponent,
        flags=flags,
        error_exponent=unit_exponent - 1 if inexact else None,
    )
    rounded = Fraction(document["coefficient"]) * power2(document["exponent"])
    if inexact:
        assert abs(rounded - value) <= power2(document["error_exponent"])
    else:
        assert rounded == value
    return document


def exact_value(document):
    """Read a finite fixture operand as an exact rational."""
    return Fraction(document.get("coefficient", 0)) * power2(document.get("exponent", 0))


def operand(document):
    """Remove diagnostics from a rounded result."""
    return {
        "coefficient": document["coefficient"],
        "exponent": document["exponent"],
        "zero_sign": document["zero_sign"],
    }


def binary64_fraction(bits):
    """Decode finite IEEE binary64 bits independently."""
    sign = -1 if bits >> 63 else 1
    exponent = bits >> 52 & 0x7FF
    fraction = bits & ((1 << 52) - 1)
    assert exponent != 0x7FF
    if exponent == 0:
        return sign * Fraction(fraction) * power2(-1074)
    return sign * Fraction((1 << 52) | fraction) * power2(exponent - 1023 - 52)


def float32_bits(value, negative_zero=False):
    """Encode an exactly representable Fraction with a host-independent check."""
    if value == 0:
        return 0x80000000 if negative_zero else 0
    host = float(value)
    assert Fraction(host) == value
    packed = struct.unpack(">I", struct.pack(">f", host))[0]
    decoded = struct.unpack(">f", struct.pack(">I", packed))[0]
    assert Fraction(decoded) == value
    return packed


def codec_case(bits):
    """Derive h/l/q using exact rational rounding."""
    sign = -1 if bits >> 63 else 1
    exponent_field = bits >> 52 & 0x7FF
    fraction = bits & ((1 << 52) - 1)
    assert exponent_field != 0x7FF
    if exponent_field == 0 and fraction == 0:
        sign_tag = int(sign < 0)
        return {
            "bits": f"{bits:016x}",
            "codec": {
                "high_bits": f"{sign_tag << 31:08x}",
                "low_bits": "00000000",
                "tail": 0,
                "exponent": 0,
                "zero_sign": sign_tag,
            },
        }
    if exponent_field == 0:
        shift = 53 - fraction.bit_length()
        significand = fraction << shift
        exponent = -1021 - shift
    else:
        significand = (1 << 52) | fraction
        exponent = exponent_field - 1022
    normalized = sign * Fraction(significand, 1 << 53)
    high_doc = round_fraction(normalized, FP32)
    high = exact_value(high_doc)
    low_doc = round_fraction(normalized - high, FP32)
    low = exact_value(low_doc)
    tail = (normalized - high - low) * (1 << 53)
    assert tail.denominator == 1 and -8 <= tail <= 8
    return {
        "bits": f"{bits:016x}",
        "codec": {
            "high_bits": f"{float32_bits(high):08x}",
            "low_bits": f"{float32_bits(low):08x}",
            "tail": int(tail),
            "exponent": exponent,
            "zero_sign": 0,
        },
    }


def sqrt_result(value, format_tuple):
    """Round sqrt(value) by comparing exact squared midpoints."""
    if value < 0:
        return result_document(invalid=True, flags=("invalid",))
    if value == 0:
        return result_document()
    precision, minimum_normal, _ = format_tuple
    minimum_unit = minimum_normal - (precision - 1)
    result_exponent = floor_log2(value) // 2
    unit_exponent = max(result_exponent - (precision - 1), minimum_unit)
    scaled = value / power2(2 * unit_exponent)
    quotient = math.isqrt(scaled.numerator // scaled.denominator)
    midpoint = Fraction(2 * quotient + 1, 2)
    if scaled > midpoint * midpoint or (
        scaled == midpoint * midpoint and quotient & 1
    ):
        quotient += 1
    exact = scaled == quotient * quotient
    if quotient >= 1 << precision:
        quotient >>= 1
        unit_exponent += 1
    flags = []
    if quotient < 1 << (precision - 1) and not exact:
        flags.append("underflow")
    if not exact:
        flags.append("inexact")
    result = result_document(
        coefficient=quotient,
        exponent=unit_exponent,
        flags=flags,
        error_exponent=unit_exponent - 1 if not exact else None,
    )
    rounded = exact_value(result)
    if not exact:
        lower = max(Fraction(), rounded - power2(unit_exponent - 1))
        upper = rounded + power2(unit_exponent - 1)
        assert lower * lower <= value <= upper * upper
    return result


def primitive_result(operation, operands, format_tuple):
    """Evaluate one primitive with exact rational intermediates."""
    values = [exact_value(item) for item in operands]
    if operation == "convert":
        return round_fraction(values[0], format_tuple, zero_sign=operands[0]["zero_sign"])
    if operation == "negate":
        if values[0] == 0:
            return result_document(zero_sign=1 - operands[0]["zero_sign"])
        return operand(round_fraction(-values[0], format_tuple)) | {
            "infinity_sign": 0,
            "invalid": False,
            "flags": [],
            "error_exponent": None,
        }
    if operation == "abs":
        if values[0] == 0:
            return result_document()
        return operand(round_fraction(abs(values[0]), format_tuple)) | {
            "infinity_sign": 0,
            "invalid": False,
            "flags": [],
            "error_exponent": None,
        }
    if operation in ("add", "subtract", "multiply", "fma"):
        if operation == "add":
            exact = values[0] + values[1]
        elif operation == "subtract":
            exact = values[0] - values[1]
        elif operation == "multiply":
            exact = values[0] * values[1]
        else:
            exact = values[0] * values[1] + values[2]
        zero_sign = 0
        if exact == 0 and operation in ("add", "subtract"):
            right_sign = operands[1]["zero_sign"] ^ int(operation == "subtract")
            zero_sign = int(values[0] == 0 and values[1] == 0 and operands[0]["zero_sign"] and right_sign)
        elif exact == 0 and operation == "multiply":
            left_sign = int(values[0] < 0) if values[0] else operands[0]["zero_sign"]
            right_sign = int(values[1] < 0) if values[1] else operands[1]["zero_sign"]
            zero_sign = left_sign ^ right_sign
        return round_fraction(exact, format_tuple, zero_sign=zero_sign)
    if operation == "divide":
        if values[1] == 0:
            if values[0] == 0:
                return result_document(invalid=True, flags=("invalid",))
            sign = -1 if (values[0] < 0) ^ bool(operands[1]["zero_sign"]) else 1
            return result_document(infinity_sign=sign, flags=("divide_by_zero",))
        zero_sign = 0
        if values[0] == 0:
            zero_sign = operands[0]["zero_sign"] ^ int(values[1] < 0)
        return round_fraction(values[0] / values[1], format_tuple, zero_sign=zero_sign)
    if operation == "sqrt":
        result = sqrt_result(values[0], format_tuple)
        if values[0] == 0:
            result["zero_sign"] = operands[0]["zero_sign"]
        return result
    raise AssertionError(operation)


def rounded_inputs(format_tuple):
    """Create boundary-heavy operands, including values unique to 64-bit precision."""
    raw = [
        Fraction(),
        -Fraction(),
        power2(-1074),
        -power2(-1074),
        power2(-1022),
        power2(-1022) - power2(-1074),
        Fraction(1, 3),
        -Fraction(1, 3),
        Fraction(1),
        -Fraction(1),
        Fraction(3, 2),
        power2(24) + 1,
        power2(53) + 1,
        power2(63) + 1,
        power2(900),
        -power2(900),
        (2 - power2(-52)) * power2(1023),
        power2(-1086),
        power2(-1085),
        power2(-1022) + power2(-1085),
    ]
    values = []
    for index, value in enumerate(raw):
        rounded = round_fraction(value, format_tuple, zero_sign=int(index == 1))
        if not rounded["infinity_sign"]:
            values.append(operand(rounded))
    return values


def primitive_cases():
    """Build deterministic boundary, tie, carry, range and cancellation cases."""
    cases = []
    for identity, format_tuple in FORMATS.items():
        values = rounded_inputs(format_tuple)
        for value in values:
            for operation in ("convert", "negate", "abs"):
                operands = [value]
                cases.append(
                    {
                        "format": identity,
                        "operation": operation,
                        "operands": operands,
                        "result": primitive_result(operation, operands, format_tuple),
                    }
                )
        pairs = [(left, right) for left in values for right in values]
        # Fixed stride covers opposite signs, extremes, zeros and non-dyadic inputs.
        selected = pairs[:: max(1, len(pairs) // 96)][:128]
        for operation in ("add", "subtract", "multiply", "divide"):
            for left, right in selected:
                operands = [left, right]
                cases.append(
                    {
                        "format": identity,
                        "operation": operation,
                        "operands": operands,
                        "result": primitive_result(operation, operands, format_tuple),
                    }
                )
        for index in range(min(48, len(selected))):
            left, right = selected[index]
            addend = values[-1 - index % len(values)]
            operands = [left, right, addend]
            cases.append(
                {
                    "format": identity,
                    "operation": "fma",
                    "operands": operands,
                    "result": primitive_result("fma", operands, format_tuple),
                }
            )
        for value in values:
            operands = [value]
            cases.append(
                {
                    "format": identity,
                    "operation": "sqrt",
                    "operands": operands,
                    "result": primitive_result("sqrt", operands, format_tuple),
                }
            )
        precision = format_tuple[0]
        maximum = operand(round_fraction((2 - power2(1 - precision)) * power2(1023), format_tuple))
        two = operand(round_fraction(Fraction(2), format_tuple))
        negative_maximum = operand(round_fraction(-(2 - power2(1 - precision)) * power2(1023), format_tuple))
        operands = [maximum, two, negative_maximum]
        cases.append(
            {
                "format": identity,
                "operation": "fma",
                "operands": operands,
                "result": primitive_result("fma", operands, format_tuple),
                "purpose": "finite result despite overflowing separately rounded product",
            }
        )
    return cases


def reduction_result(operation, left, right, kind, format_tuple, repeat):
    """Compute one exact reduction with a single output rounding."""
    left_values = [exact_value(item) for item in left] * repeat
    if operation == "sum":
        return round_fraction(sum(left_values, Fraction()), format_tuple)
    if operation == "dot":
        right_values = [exact_value(item) for item in right] * repeat
        return round_fraction(
            sum((a * b for a, b in zip(left_values, right_values)), Fraction()),
            format_tuple,
        )
    if kind == "inf":
        maximum = max(map(abs, left_values), default=Fraction())
        return round_fraction(maximum, format_tuple)
    if kind == 1:
        return round_fraction(sum(map(abs, left_values), Fraction()), format_tuple)
    squares = sum((value * value for value in left_values), Fraction())
    return sqrt_result(squares, format_tuple)


def reduction_cases():
    """Cover cancellation, odd reduction lengths and a 65536-term path."""
    cases = []
    for identity, format_tuple in FORMATS.items():
        values = rounded_inputs(format_tuple)
        vectors = [
            (values[:3], 1),
            ([values[8], values[10], values[9]], 11),
            ([values[14], values[8], values[15], values[2]], 8),
            ([values[8]], 65_536),
        ]
        for left, repeat in vectors:
            for operation, kind in (("sum", None), ("norm", 1), ("norm", 2), ("norm", "inf")):
                result = reduction_result(operation, left, [], kind, format_tuple, repeat)
                cases.append(
                    {
                        "format": identity,
                        "operation": operation,
                        "kind": kind,
                        "left": left,
                        "repeat": repeat,
                        "result": result,
                    }
                )
            right = list(reversed(left))
            cases.append(
                {
                    "format": identity,
                    "operation": "dot",
                    "kind": None,
                    "left": left,
                    "right": right,
                    "repeat": repeat,
                    "result": reduction_result("dot", left, right, None, format_tuple, repeat),
                }
            )
    return cases


def comparison_and_projection_cases():
    """Provide independent exact ordering and tagged-bound projections."""
    comparisons = []
    projections = []
    for identity, format_tuple in FORMATS.items():
        values = rounded_inputs(format_tuple)
        for left, right in zip(values, reversed(values)):
            a, b = exact_value(left), exact_value(right)
            comparisons.append(
                {"format": identity, "left": left, "right": right, "result": (a > b) - (a < b)}
            )
        lower, upper = values[7], values[10]
        for value in values:
            exact = exact_value(value)
            projected = lower if exact < exact_value(lower) else upper if exact > exact_value(upper) else value
            projections.append(
                {"format": identity, "value": value, "lower": lower, "upper": upper, "result": projected}
            )
            projections.append(
                {"format": identity, "value": value, "lower": None, "upper": upper, "result": upper if exact > exact_value(upper) else value}
            )
    return comparisons, projections


def codec_cases():
    """Cover every binary64 exponent/sign and deterministic tie/carry fractions."""
    bits = {0, 1 << 63, 1, (1 << 63) | 1, (1 << 52) - 1, (1 << 63) | ((1 << 52) - 1)}
    fractions = (0, 1, (1 << 28) - 1, 1 << 28, (1 << 52) - 2, (1 << 52) - 1)
    for exponent in range(1, 2047):
        for sign in (0, 1):
            for fraction in fractions:
                bits.add(sign << 63 | exponent << 52 | fraction)
    for bit in range(52):
        for sign in (0, 1):
            bits.add(sign << 63 | 1 << bit)
    rng = random.Random(SEED)
    for _ in range(8192):
        bits.add(
            rng.getrandbits(1) << 63
            | rng.randrange(2047) << 52
            | rng.getrandbits(52)
        )
    cases = [codec_case(value) for value in sorted(bits)]
    assert {case["codec"]["tail"] for case in cases} == set(range(-8, 9))
    return cases


def build_fixture():
    """Build the complete reproducible oracle document."""
    codecs = codec_cases()
    comparisons, projections = comparison_and_projection_cases()
    document = {
        "schema": "lp-expansion-oracle-v1",
        "scope": "CPU proof/oracle validation only; no solver or device behavior",
        "seed": SEED,
        "formats": {
            key: {
                "precision": value[0],
                "minimum_normal_exponent": value[1],
                "maximum_exponent": value[2],
                "minimum_subnormal_exponent": value[1] - value[0] + 1,
            }
            for key, value in FORMATS.items()
        },
        "codec_cases": codecs,
        "primitive_cases": primitive_cases(),
        "reduction_cases": reduction_cases(),
        "comparison_cases": comparisons,
        "projection_cases": projections,
    }
    encoded_inputs = b"".join(bytes.fromhex(case["bits"]) for case in codecs)
    document["codec_input_sha256"] = hashlib.sha256(encoded_inputs).hexdigest()
    return document


def encoded_fixture():
    """Return canonical serialized fixture bytes."""
    return json.dumps(build_fixture(), sort_keys=True, separators=(",", ":")) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args()
    encoded = encoded_fixture()
    if args.write:
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(encoded)
    else:
        assert FIXTURE.read_text() == encoded, "GPUP-REP oracle fixture changed"
    fixture = json.loads(encoded)
    print(
        "PASS: GPUP-REP exact-rational oracle; "
        f"{len(fixture['codec_cases'])} codec, "
        f"{len(fixture['primitive_cases'])} primitive, "
        f"{len(fixture['reduction_cases'])} reduction cases; no GPU work"
    )


if __name__ == "__main__":
    main()
