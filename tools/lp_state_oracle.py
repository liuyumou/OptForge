"""Independent exact-rational GPUP-STATE transcendental admission oracle.

Log uses the alternating log(1+t) series; exp uses argument halving, an exact
Taylor enclosure, and outward-rounded squaring. No candidate arithmetic,
rounding, intervals, or decoding helpers are imported.
"""

from fractions import Fraction
from functools import lru_cache

from lp_expansion_oracle import power2, floor_log2, round_fraction


FORMATS = {"matched-fp64": (53, -1022, 1023),
           "compensated-pair": (48, -1022, 1023),
           "expansion64": (64, -1022, 1023)}


def value(document):
    if document["invalid"] or document["infinity_sign"]:
        raise ValueError("nonfinite_operand")
    return document["coefficient"] * power2(document["exponent"])


def log1p_interval(t, terms=400):
    if not Fraction(-1, 4) <= t <= Fraction(1, 2):
        raise ValueError("oracle_log_reduction")
    result = Fraction(0)
    term = t
    for k in range(1, terms + 1):
        result += term / k if k & 1 else -term / k
        term *= t
    remainder = abs(term) / ((terms + 1) * (1 - abs(t)))
    return result - remainder, result + remainder


@lru_cache(maxsize=1)
def log2_interval():
    a = log1p_interval(Fraction(1, 2))
    b = log1p_interval(Fraction(1, 3))
    return a[0] + b[0], a[1] + b[1]


def logarithm_interval(x):
    if x <= 0:
        raise ValueError("log_domain")
    exponent = floor_log2(x)
    mantissa = x / power2(exponent)
    if mantissa > Fraction(3, 2):
        mantissa /= 2
        exponent += 1
    lo, hi = log1p_interval(mantissa - 1)
    l2 = log2_interval()
    offsets = [exponent * endpoint for endpoint in l2]
    return lo + min(offsets), hi + max(offsets)


def exponential_interval(x):
    count = 0
    reduced = x
    while abs(reduced) > Fraction(1, 8):
        reduced /= 2
        count += 1
    if count > 14:
        raise ValueError("oracle_exp_range")
    term = Fraction(1)
    total = term
    for k in range(1, 81):
        term *= reduced / k
        total += term
    error = 2 * abs(term * reduced / 81)
    lo, hi = total - error, total + error
    # Absolute outward error must resolve the full subnormal output range too.
    grid = 1 << 2048
    for _ in range(count):
        lower, upper = lo * lo * grid, hi * hi * grid
        lo = Fraction(lower.numerator // lower.denominator, grid)
        hi = Fraction(-((-upper.numerator) // upper.denominator), grid)
    return lo, hi


def expected(operation, operand, target):
    x = value(operand)
    if operation == "ln" and x == 1:
        return round_fraction(Fraction(0), target)
    if operation == "exp" and x == 0:
        return round_fraction(Fraction(1), target)
    interval = logarithm_interval(x) if operation == "ln" else exponential_interval(x)
    left, right = (round_fraction(endpoint, target) for endpoint in interval)
    if (left["coefficient"], left["exponent"], left["zero_sign"], left["infinity_sign"]) != (
            right["coefficient"], right["exponent"], right["zero_sign"], right["infinity_sign"]):
        raise ValueError("oracle_rounding_ambiguous")
    return left
