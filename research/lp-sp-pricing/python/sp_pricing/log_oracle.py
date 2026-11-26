"""Section 5.5 rational logarithm proxies and exact affine sign comparisons.

The caller supplies the theorem's uniform threshold T and eta. Large logarithms
stay symbolic until a sign comparison. Resource admission checks the resulting
rational product before allocating it. This component is independent of the
direct calibration used by the current practical solver.
"""
from fractions import Fraction as Q
import math
from .exact import rational, Limit
from .calibration import floor_log2
from .compression import nearest


class LogOracle:
    def __init__(self, minor, eta, threshold, work):
        self.minor, self.eta, self.threshold, self.work = minor, rational(eta), threshold, work
        if not 0 < self.eta < 1 or self.eta.numerator != 1 or self.eta.denominator & (self.eta.denominator-1) or threshold < 1:
            raise ValueError("dyadic reciprocal eta and positive threshold required")
        self.cache = {}

    def proxy(self, index):
        if index in self.cache:
            return self.cache[index]
        value = abs(rational(self.minor(index)))
        if not value:
            raise ValueError("zero minor has no logarithm")
        sign = 1 if value >= 1 else -1
        z = value if sign == 1 else 1/value
        integer = floor_log2(z)
        if integer >= self.threshold:
            result = dict(kind="exact_log", minor=value)
        else:
            z /= self.work.power2(integer)
            steps = self.eta.denominator.bit_length()-1+6
            def series(argument):
                q = 1-1/argument
                power, total = Q(1), Q(0)
                for j in range(1, steps+1):
                    power *= q; total += power/j
                    self.work.tick(power, total)
                return total
            approximate = sign*(integer+series(z)/series(Q(2)))
            result = dict(kind="rational_proxy", value=nearest(approximate/self.eta)*self.eta)
        self.cache[index] = result
        return result

    def sign(self, constant, coefficients):
        constant = rational(constant)
        symbolic = []
        for index, coefficient in coefficients.items():
            coefficient = rational(coefficient)
            if not coefficient:
                continue
            proxy = self.proxy(index)
            if proxy["kind"] == "rational_proxy":
                constant += coefficient*proxy["value"]
            else:
                symbolic.append((coefficient, proxy["minor"]))
        if not symbolic:
            return int(constant > 0)-int(constant < 0)
        denominator = math.lcm(constant.denominator, *(c.denominator for c, _ in symbolic))
        exponent = int(constant*denominator)
        entries = [(int(c*denominator), minor) for c, minor in symbolic]
        bound = abs(exponent)+1+sum(abs(c)*max(minor.numerator.bit_length(), minor.denominator.bit_length()) for c, minor in entries)
        if bound > self.work.max_bits:
            raise Limit("log_comparison_product_bit_admission")
        product = self.work.power2(exponent)
        for coefficient, minor in entries:
            product *= minor**coefficient
            self.work.tick(product)
        return int(product > 1)-int(product < 1)
