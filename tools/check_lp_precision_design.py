#!/usr/bin/env python3
"""CPU-only exact examples for the proposed LP precision design, not a solver codec.

No project benchmark seed, manifest, runtime setting or GPU resource is used.
The finite samples support the written proof; they do not prove all binary64 cases.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import struct
from fractions import Fraction as F


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def two(exponent):
    return F(1 << exponent) if exponent >= 0 else F(1, 1 << -exponent)


def rn_significand(value, precision):
    """Integer/rational ties-to-even rounding; no hardware FP32 arithmetic."""
    if not value:
        return F(0)
    sign = -1 if value < 0 else 1
    magnitude = abs(value)
    exponent = magnitude.numerator.bit_length() - magnitude.denominator.bit_length()
    if magnitude < two(exponent):
        exponent -= 1
    unit = two(exponent - precision + 1)
    scaled = magnitude / unit
    quotient, remainder = divmod(scaled.numerator, scaled.denominator)
    if 2 * remainder > scaled.denominator or (
        2 * remainder == scaled.denominator and quotient % 2
    ):
        quotient += 1
    return sign * quotient * unit


def fp32(value):
    return struct.unpack('>f', struct.pack('>f', float(value)))[0]


def bits_of(value):
    return struct.unpack('>Q', struct.pack('>d', value))[0]


def normalize_bits(bits):
    sign = -1 if bits >> 63 else 1
    exponent = (bits >> 52) & 2047
    fraction = bits & ((1 << 52) - 1)
    require(exponent != 2047, 'nonfinite input is outside this finite codec example')
    if exponent == 0:
        if fraction == 0:
            return F(0), 0
        shift = 53 - fraction.bit_length()
        mantissa = fraction << shift
        scale = -1021 - shift
    else:
        mantissa = (1 << 52) + fraction
        scale = exponent - 1022
    return sign * F(mantissa, 1 << 53), scale


def split(bits):
    m, e = normalize_bits(bits)
    h = rn_significand(m, 24)
    low = rn_significand(m - h, 24)
    q = (m - h - low) * (1 << 53)
    require(q.denominator == 1 and -8 <= q <= 8, 'tail violates proved bound')
    require(F(fp32(m)) == h, 'host FP32 high conversion disagrees with integer oracle')
    require(F(fp32(m - h)) == low, 'host FP32 low conversion disagrees with integer oracle')
    original = struct.unpack('>d', struct.pack('>Q', bits))[0]
    decoded = (h + low + q * two(-53)) * two(e)
    require(decoded == F(original), 'real value did not round trip')
    # Zero sign is a separate tag, since rational zero has no sign.
    recovered = bits_of(float(decoded)) if decoded else bits & (1 << 63)
    require(recovered == bits, 'finite bits did not round trip')
    require(-1073 <= e <= 1024, 'scale outside int16-supported binary64 range')
    return m, e, h, low, int(q)


def dot(left, right):
    return sum((a * b for a, b in zip(left, right)), F(0))


def matvec(matrix, vector):
    return [dot(row, vector) for row in matrix]


def transpose(matrix):
    return [list(column) for column in zip(*matrix)]


def subtract(left, right):
    return [a - b for a, b in zip(left, right)]


def algebra_examples():
    # An infeasible anchor and a feasible target exercise shifted bounds/residuals.
    matrix = [[F(2), F(-3), F(-1), F(0)], [F(1), F(4), F(0), F(-1)]]
    anchor = list(map(F, [2, -1, 1, -2]))
    target = list(map(F, [1, 2, -4, 9]))
    bounds = [(None, F(3)), (F(2), F(2)), (F(-4), F(2)), (None, F(10))]
    y0, w = list(map(F, [2, -3])), list(map(F, [5, -7]))
    rp = [-value for value in matvec(matrix, anchor)]
    by0 = matvec(transpose(matrix), y0)
    corrections = 0
    for sense in (1, -1):
        g = [sense * F(3), sense * F(-5), F(0), F(0)]
        offset = sense * F(7)
        rd = subtract(g, by0)
        for ep in (-10, -1, 0, 1, 10):
            for ed in (-10, -1, 0, 1, 10):
                dp, dd = two(ep), two(ed)
                d = [dp * value for value in subtract(target, anchor)]
                require(matvec(matrix, d) == [dp * r for r in rp], 'correction feasibility')
                correction_cost = dot([dd * value for value in rd], d)
                reconstructed = dot(g, anchor) + offset + dot(y0, rp) + correction_cost / (dp * dd)
                require(reconstructed == dot(g, target) + offset, 'correction objective map')
                y_next = [y + z / dd for y, z in zip(y0, w)]
                lhs = subtract([dd * r for r in rd], matvec(transpose(matrix), w))
                rhs = [dd * r for r in subtract(g, matvec(transpose(matrix), y_next))]
                require(lhs == rhs, 'dual scaling map')
                for (lo, hi), v0, value, change in zip(bounds, anchor, target, d):
                    if lo is not None:
                        require((value >= lo) == (change >= dp * (lo - v0)), 'lower bound map')
                    if hi is not None:
                        require((value <= hi) == (change <= dp * (hi - v0)), 'upper bound map')
                perturbation = [[F(1, 1024), F(-1, 2048), F(0), F(0)],
                                [F(1, 4096), F(1, 1024), F(0), F(0)]]
                bhat = [[a + error for a, error in zip(row, errors)]
                        for row, errors in zip(matrix, perturbation)]
                # Use a deliberately inexact correction, not only the feasible d.
                trial_d = [d[0] + F(1, 8), *d[1:]]
                eta = subtract(matvec(bhat, trial_d), [dp * r for r in rp])
                updated = [v + change / dp for v, change in zip(anchor, trial_d)]
                actual = [-value for value in matvec(matrix, updated)]
                expected = [(error - residual) / dp for error, residual in
                            zip(matvec(perturbation, trial_d), eta)]
                require(actual == expected, 'inexact correction residual identity')
                delta = subtract(target, anchor)
                estimate = [a + b for a, b in zip(matvec(matrix, anchor), matvec(bhat, delta))]
                require(subtract(estimate, matvec(matrix, target)) == matvec(perturbation, delta),
                        'anchored product error identity')
                for row, actual_error in zip(perturbation, matvec(perturbation, delta)):
                    envelope = sum(map(abs, row), F(0)) * max(map(abs, delta))
                    require(abs(actual_error) <= envelope, 'row activity bound')
                corrections += 1
    proximal = 0
    for lo, hi in [(F(-2), F(3)), (F(0), F(0)), (None, F(3)), (F(-2), None), (None, None)]:
        for exponent in (-10, 0, 10):
            sigma = two(exponent)
            points = {F(k, 2) for k in range(-10, 11)}
            for bound in (lo, hi):
                if bound is not None:
                    points.update(sigma * bound + delta for delta in (F(0), two(-20), -two(-20)))
            for z in sorted(points):
                clipped = z / sigma
                if lo is not None:
                    clipped = max(lo, clipped)
                if hi is not None:
                    clipped = min(hi, clipped)
                old = z - sigma * clipped
                if lo is not None and z < sigma * lo:
                    new = z - sigma * lo
                elif hi is not None and z > sigma * hi:
                    new = z - sigma * hi
                else:
                    new = F(0)
                require(old == new, 'support proximal identity')
                proximal += 1
    a = [[F(2), F(-3)], [F(1), F(4)]]
    x, y, slack = list(map(F, [1, 2])), list(map(F, [2, -3])), [F(1, 8), F(1, 4)]
    b, c = list(map(F, [7, 5])), list(map(F, [3, -5]))
    rp = subtract(b, matvec(a, x))
    rd = subtract(subtract(c, matvec(transpose(a), y)), slack)
    require(dot(c, x) - dot(b, y) == dot(x, slack) + dot(x, rd) - dot(y, rp), 'gap identity')
    original = [F(x) for x in (0, 1)]
    wrong = [-F(x) for x in (0, 1)]
    activity = [-F(x) + 2 * F(x) for x in (0, 1)]
    require(original.index(min(original)) != wrong.index(min(wrong)), 'ranged-row counterexample')
    require(activity == original, 'activity variable restores objective')
    return {'correction_scale_and_sense_cases': corrections, 'proximal_cases': proximal,
            'gap_identity': True, 'naive_ranged_cost_changes_minimizer': True,
            'activity_cost_restores_original': True}


def build_report():
    samples = {0, 1 << 63, 1, (1 << 63) | 1, (1 << 52) - 1, (1 << 63) | ((1 << 52) - 1)}
    fractions = (0, 1, (1 << 28) - 1, 1 << 28, (1 << 52) - 2, (1 << 52) - 1)
    for exponent in range(1, 2047):
        for fraction in fractions:
            for sign in (0, 1):
                samples.add((sign << 63) | (exponent << 52) | fraction)
    for bit in range(52):
        for sign in (0, 1):
            samples.add((sign << 63) | (1 << bit))
    rng = random.Random(17003)  # Design examples only; not a benchmark seed.
    for _ in range(32768):
        samples.add((rng.getrandbits(1) << 63) | (rng.randrange(2047) << 52) | rng.getrandbits(52))
    example_bits = bits_of(float.fromhex('0x1.23456789abcdep-1'))
    samples.add(example_bits)
    q_values = set()
    for bits in sorted(samples):
        q_values.add(split(bits)[-1])
    require(q_values == set(range(-8, 9)), 'sample should exercise every tail code')
    m, e, high, low, q = split(example_bits)
    raw_tail = q * two(-53)
    raw_half = struct.unpack('>e', struct.pack('>e', float(raw_tail)))[0]
    require(raw_half == 0 and raw_tail != 0, 'raw FP16 tail loses information')
    for integer in range(-8, 9):
        require(rn_significand(F(integer), 3) == integer, 'E5M2 integer-tail precision')
        require(rn_significand(F(integer), 4) == integer, 'E4M3 integer-tail precision')
        require(rn_significand(integer * two(-53), 8) == integer * two(-53), 'BF16 tail precision')
    class Parts3(ctypes.Structure):
        _fields_ = [('parts', ctypes.c_float * 3), ('exponent', ctypes.c_int32)]
    class HalfI32(ctypes.Structure):
        _fields_ = [('parts', ctypes.c_float * 2), ('tail_bits', ctypes.c_uint16), ('exponent', ctypes.c_int32)]
    class HalfI16(ctypes.Structure):
        _fields_ = [('parts', ctypes.c_float * 2), ('tail_bits', ctypes.c_uint16), ('exponent', ctypes.c_int16)]
    sizes = {'parts3_i32': ctypes.sizeof(Parts3), 'two_fp32_half_i32': ctypes.sizeof(HalfI32),
             'two_fp32_half_i16': ctypes.sizeof(HalfI16), 'two_fp32_i8_i16_separate_arrays_payload': 11}
    require(sizes == {'parts3_i32': 16, 'two_fp32_half_i32': 16, 'two_fp32_half_i16': 12,
                      'two_fp32_i8_i16_separate_arrays_payload': 11}, 'unexpected host ABI')
    lost = fp32(fp32(1 << 24) + 1) - fp32(1 << 24)
    require(lost == 0, 'FP32 small-update counterexample')
    digest = hashlib.sha256(b''.join(struct.pack('>Q', value) for value in sorted(samples))).hexdigest()
    return {'schema': 'lp-precision-design-examples-v1',
            'scope': 'CPU exact design examples; not runtime, GPU acceptance, or exhaustive proof',
            'codec': {'finite_patterns': len(samples), 'input_bits_sha256': digest,
                      'sample_seed_not_benchmark_seed': 17003, 'tail_integers_observed': sorted(q_values),
                      'all_normal_exponent_fields_and_both_signs': True, 'signed_zero_preserved_by_tag': True},
            'example': {'m_hex': float(m).hex(), 'exponent': e, 'high_hex': float(high).hex(),
                        'low_hex': float(low).hex(), 'tail_integer': q, 'raw_tail_hex': float(raw_tail).hex(),
                        'raw_half_hex': raw_half.hex()},
            'linux_host_abi_bytes': sizes,
            'fp32_small_update': {'expression': '(2^24 + 1) - 2^24', 'exact': 1, 'fp32': int(lost)},
            'lp_identities': algebra_examples()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    output = parser.add_mutually_exclusive_group()
    output.add_argument('--write', type=Path, help='write reproducible design artifact')
    output.add_argument('--check', type=Path, help='compare with existing artifact without changing it')
    args = parser.parse_args()
    report = build_report()
    encoded = json.dumps(report, sort_keys=True, indent=2) + '\n'
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(encoded)
    elif args.check:
        require(args.check.read_text() == encoded, 'design artifact differs; inspect before replacing')
    else:
        print(encoded, end='')
    if args.write or args.check:
        print(f"PASS: {report['codec']['finite_patterns']} finite patterns, "
              f"{report['lp_identities']['correction_scale_and_sense_cases']} correction cases, "
              f"{report['lp_identities']['proximal_cases']} proximal cases; no GPU work")


if __name__ == '__main__':
    main()
