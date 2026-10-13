"""CPU-only GPUP-STATE admission: integer interval control primitives.

This is mathematical validation tooling, not a solver or SDK. The independent
Fraction oracle does not import this module. Existing GPUP-REP fixtures remain
unchanged. Working precision means endpoint resolution; multiplication uses
twice that width before directed truncation.
"""

from functools import lru_cache

from lp_expansion_candidate import (
    ArithmeticRefusal, BinaryFormat, Rounded, EXPANSION64, BINARY64,
    round_rational, normalize, multiply, add, compare, square_root, norm,
)


PAIR48 = BinaryFormat("fp32-24-24-pair-rne-v1", 48, -1022, 1023)
WORKING_BITS = (128, 192, 256)
MAX_TERMS = 288


def finite(value):
    if any(type(field) is not int for field in (value.coefficient, value.exponent, value.zero_sign, value.infinity_sign)):
        raise ArithmeticRefusal("operand_integer_field")
    if value.zero_sign not in (0, 1) or type(value.invalid) is not bool:
        raise ArithmeticRefusal("operand_encoding")
    if value.invalid or value.infinity_sign:
        raise ArithmeticRefusal("nonfinite_operand")
    return value.coefficient, value.exponent


def scaled(value, bits):
    """Directed integer interval for value * 2**bits."""
    n, e = finite(value)
    shift = e + bits
    if shift >= 0:
        return n << shift, n << shift
    d = 1 << -shift
    return n // d, -((-n) // d)


def imul(a, b, bits):
    products = [x * y for x in a for y in b]
    unit = 1 << bits
    return min(products) // unit, -((-max(products)) // unit)


def iadd(a, b):
    return a[0] + b[0], a[1] + b[1]


def idiv_int(a, divisor):
    if divisor <= 0:
        raise ArithmeticRefusal("interval_divisor")
    return a[0] // divisor, -((-a[1]) // divisor)


def atanh_interval(numerator, denominator, bits):
    """2*atanh(z), 0<=z<=1/3, with an explicit positive tail."""
    if not 0 <= numerator * 3 <= denominator:
        raise ArithmeticRefusal("log_reduction_domain")
    unit = 1 << bits
    z = (numerator * unit // denominator,
         -((-numerator * unit) // denominator))
    z2 = imul(z, z, bits)
    term = z
    total = (0, 0)
    count = bits // 3 + 16
    for k in range(count):
        total = iadd(total, idiv_int(term, 2 * k + 1))
        term = imul(term, z2, bits)
    # Remaining sum <= z**(2N+1)/((2N+1)*(1-z*z)).
    tail_divisor = (2 * count + 1) * (unit - z2[1])
    tail = -((-term[1] * unit) // tail_divisor)
    return 2 * total[0], 2 * (total[1] + tail)


@lru_cache(maxsize=3)
def ln2_interval(bits):
    return atanh_interval(1, 3, bits)


def log_interval(value, bits):
    n, e = finite(value)
    if n <= 0:
        raise ArithmeticRefusal("log_domain")
    top = n.bit_length() - 1
    integer = top + e
    denominator = 1 << top
    mantissa = atanh_interval(n - denominator, n + denominator, bits)
    lo, hi = ln2_interval(bits)
    offset = (integer * lo, integer * hi)
    return iadd(mantissa, (min(offset), max(offset)))


def exp_interval(value, bits):
    """exp(value)=2**q*exp(r), with 0<=r<ln(2)."""
    x = scaled(value, bits)
    l2 = ln2_interval(bits)
    quotients = [a // b for a in x for b in l2]
    if min(quotients) != max(quotients):
        raise ArithmeticRefusal("exp_reduction_ambiguous")
    q = quotients[0]
    offset = (q * l2[0], q * l2[1])
    remainder = (x[0] - max(offset), x[1] - min(offset))
    unit = 1 << bits
    if not 0 <= remainder[0] <= remainder[1] < unit:
        raise ArithmeticRefusal("exp_reduction_ambiguous")
    term = (unit, unit)
    total = term
    count = bits + 16
    if count > MAX_TERMS:
        raise ArithmeticRefusal("transcendental_work")
    for k in range(1, count + 1):
        term = idiv_int(imul(term, remainder, bits), k)
        total = iadd(total, term)
    next_term = idiv_int(imul(term, remainder, bits), count + 1)
    # Since r<1, all subsequent ratios <=1/(N+2)<=1/2.
    return (total[0], total[1] + 2 * next_term[1]), q


def rounded_interval(interval, exponent, target):
    left = round_rational(interval[0], 1, exponent, target)
    right = round_rational(interval[1], 1, exponent, target)
    if left.plain() != right.plain():
        return None
    if left.infinity_sign:
        return Rounded(infinity_sign=left.infinity_sign, flags=("overflow", "inexact"))
    unit = target.minimum_unit_exponent if not left.coefficient else left.exponent
    flags = ("underflow", "inexact") if abs(left.coefficient) < 1 << (target.precision - 1) else ("inexact",)
    return Rounded(left.coefficient, left.exponent, left.zero_sign,
                   flags=flags, error_exponent=unit - 1)


def logarithm(value, target, working_bits=WORKING_BITS):
    n, e = finite(value)
    if abs(n).bit_length() > 64 or not -1085 <= e <= 1023:
        raise ArithmeticRefusal("transcendental_input_range")
    if n <= 0:
        raise ArithmeticRefusal("log_domain")
    if e <= 0 and n == 1 << -e:
        return Rounded()
    for bits in working_bits:
        if bits not in WORKING_BITS:
            raise ArithmeticRefusal("working_precision")
        result = rounded_interval(log_interval(value, bits), -bits, target)
        if result is not None:
            return result
    raise ArithmeticRefusal("log_rounding_ambiguous")


def exponential(value, target, working_bits=WORKING_BITS):
    n, e = finite(value)
    if abs(n).bit_length() > 64 or not -1085 <= e <= 1023:
        raise ArithmeticRefusal("transcendental_input_range")
    if n == 0:
        return normalize(Rounded(1, 0), target)
    # These bounds lie beyond every format's overflow/half-min-subnormal limits.
    if compare(value, Rounded(1024, 0)) >= 0:
        return Rounded(infinity_sign=1, flags=("overflow", "inexact"))
    if compare(value, Rounded(-1024, 0)) <= 0:
        return Rounded(flags=("underflow", "inexact"), error_exponent=target.minimum_unit_exponent - 1)
    for bits in working_bits:
        if bits not in WORKING_BITS:
            raise ArithmeticRefusal("working_precision")
        try:
            interval, q = exp_interval(value, bits)
        except ArithmeticRefusal as error:
            if str(error) != "exp_reduction_ambiguous":
                raise
            continue
        result = rounded_interval(interval, q - bits, target)
        if result is not None:
            return result
    raise ArithmeticRefusal("exp_rounding_ambiguous")


def support_prox(value, step, lower, upper, target):
    """Stable prox for tagged [lower,upper], including infinite endpoints."""
    finite(value)
    finite(step)
    if compare(step, Rounded()) <= 0:
        raise ArithmeticRefusal("step_domain")
    for bound in (lower, upper):
        if bound is not None:
            finite(bound)
    if lower is not None and upper is not None and compare(lower, upper) > 0:
        raise ArithmeticRefusal("invalid_bounds")
    lo = multiply(step, lower, target) if lower is not None else None
    hi = multiply(step, upper, target) if upper is not None else None
    for endpoint in (lo, hi):
        if endpoint is not None and endpoint.infinity_sign:
            raise ArithmeticRefusal("prox_scaled_endpoint_range")
    if lo is not None and compare(value, lo) < 0:
        return add(value, lo, target, subtract=True)
    if hi is not None and compare(value, hi) > 0:
        return add(value, hi, target, subtract=True)
    return Rounded()


def bounded_dot(left, right, target):
    """Exact 320-bit admitted dot; never drops a term outside its window."""
    if len(left) != len(right) or len(left) > 65536:
        raise ArithmeticRefusal("dot_shape")
    terms = []
    for a, b in zip(left, right):
        ac, ae = finite(a)
        bc, be = finite(b)
        if abs(ac).bit_length() > 64 or abs(bc).bit_length() > 64:
            raise ArithmeticRefusal("operand_width")
        if ac and bc:
            terms.append((ac * bc, ae + be))
    if not terms:
        return Rounded()
    low = min(e for _, e in terms)
    if max(e for _, e in terms) - low > 128:
        raise ArithmeticRefusal("dot_exponent_window")
    total = sum(n << (e - low) for n, e in terms)
    if abs(total).bit_length() > 319:
        raise ArithmeticRefusal("accumulator_overflow")
    return round_rational(total, 1, low, target)
