"""Certified direct-log calibration and literal paper parameter admission.

The direct path uses the actual rational input's bit lengths. It deliberately
does not claim the dimension-only complexity of online Frank--Tardos compression.
"""
from fractions import Fraction as Q
import math
from .exact import Limit, determinant, rational, Work


def floor_log2(value):
    value = abs(rational(value))
    if not value:
        raise ValueError("log of zero")
    k = value.numerator.bit_length()-value.denominator.bit_length()
    if k >= 0:
        if value.numerator < value.denominator << k:
            k -= 1
    elif value.numerator << -k < value.denominator:
        k -= 1
    return k


def sqrt_interval(value, bits, work):
    value = rational(value)
    if value < 0:
        raise ValueError("negative radicand")
    scale = work.power2(bits)
    lower_int = math.isqrt((value.numerator << (2*bits)) // value.denominator)
    lower = Q(lower_int, int(scale))
    upper = lower if lower*lower == value else lower+1/scale
    work.tick(lower, upper)
    return lower, upper


def scaled_interval(value, exponent, bits, work):
    """Enclose value*2**exponent for the half-integral prices of Section 6."""
    exponent = rational(exponent)
    if exponent.denominator not in (1, 2):
        raise ValueError("market prices must be half integral")
    integer = exponent.numerator // exponent.denominator
    value = rational(value)
    # A normalized cofactor can be astronomically small solely because prices
    # are far apart. Enclose it near zero instead of allocating 2**|price|.
    if value and floor_log2(abs(value))+integer+2 < -bits:
        radius = work.power2(-bits)
        return -radius, radius
    base = value*work.power2(integer)
    if exponent.denominator == 1:
        return base, base
    magnitude = max(0, floor_log2(abs(base))+2) if base else 0
    lo, hi = sqrt_interval(Q(2), bits+magnitude+2, work)
    values = (base*lo, base*hi)
    work.tick(*values)
    return min(values), max(values)


def scaled_square_greater(ratio, exponent, work):
    """Compare ratio**2 * 2**exponent with one without enormous price powers."""
    exponent = int(exponent)
    lower = 2*floor_log2(abs(ratio))+exponent
    if lower >= 1:
        return True
    if lower+2 <= 0:
        return False
    numerator = ratio.numerator*ratio.numerator
    denominator = ratio.denominator*ratio.denominator
    left = numerator << max(exponent, 0)
    right = denominator << max(-exponent, 0)
    work.tick(left, right)
    return left > right


def paper_bounds(n):
    """Conservative explicit bit-size upper bounds; no enormous powers allocated.

    Equations 3.1, Section 4.3, and Lemmas 5.2--5.3 give the formulas.
    This is an allocation forecast, not a lower bound on any instance's needs.
    """
    if type(n) is not int or n < 1:
        raise ValueError("positive dimension")
    p = 10000*n*n
    e = p+6
    a_bits = e+(e+5).bit_length()
    k = (n+1).bit_length()+(n+1)*a_bits
    d = 2*n
    dissociation = (d+1)**6
    eta_bits = k+(4*dissociation).bit_length()
    extension_a_bits = k+(dissociation+4).bit_length()+eta_bits
    m_bits = (dissociation+1).bit_length()+(dissociation+1)*extension_a_bits
    m = dissociation-1
    eps_bits = 7+(m+1).bit_length()+m_bits
    c_bits = m*(m+1)+(m+1)*(1+eps_bits)
    h_bits = 7+m_bits+c_bits
    base_bits = 4+m_bits+m.bit_length()+h_bits+2
    u_bits = (m+2)*base_bits+eta_bits
    f_bits = ((dissociation+2).bit_length()
              +(dissociation+1)*(extension_a_bits+u_bits+1)+u_bits+eta_bits)
    depth = 1
    while 5**depth <= 2*n*4**depth:
        depth += 2
    return dict(N=n, precision_bits=p, compression_precision=k,
                dissociation_bound=dissociation, proxy_numerator_bits_upper=f_bits,
                demand_bound_bits_upper=f_bits+2, tree_depth=depth,
                branching=524289, leaf_count_lower=str(524289**depth),
                dense_basis_fp64_bytes=16*n*n)


class DirectCalibration:
    """Data-dependent variant: exact cofactors and actual coefficient bounds.

    Every answer approximates one true reciprocally scaled ordered basis.
    Actual circuit log demands are bounded using the rational input height.
    There is no compression restart, and no dimension-only runtime claim.
    """
    def __init__(self, b0, work):
        self.original = [list(map(rational, row)) for row in b0]
        self.work = work
        if not b0 or len(b0[0]) % 2 or any(len(row) != len(b0[0]) for row in b0):
            raise ValueError("paired basis shape")
        self.n, self.rank = len(b0[0])//2, len(b0)
        if self.rank > 2*self.n:
            raise ValueError("basis rank")
        self.cache = {}
        # Clearing all denominators bounds every nonzero minor below by
        # 2^(-rank*denominator_bits), and determinant expansion bounds it above.
        denominator_bits = sum(v.denominator.bit_length() for row in self.original for v in row)
        numerator_bits = max(abs(v.numerator).bit_length() for row in self.original for v in row)
        self.log_height = self.rank*(denominator_bits+numerator_bits+self.rank.bit_length()+2)+2
        self.demand_bound = 2*self.log_height+3
        self.epoch = 0

    def cofactor(self, row, pivots, column):
        if column in pivots:
            return Q(0)
        key = (row, tuple(pivots), column)
        if key not in self.cache:
            cols = [*pivots, column]
            self.cache[key] = determinant([[self.original[i][j] for j in cols]
                                          for i in range(row+1)], self.work)
        return self.cache[key]

    def query(self, prices, initial_bits=64):
        if len(prices) != self.n or any(rational(p).denominator not in (1, 2) for p in prices):
            raise ValueError("half-integral price vector")
        prices = list(map(rational, prices))
        bits = initial_bits
        while bits <= min(4096, self.work.max_bits//4):
            result = self._query(prices, bits)
            if result is not None:
                return result
            bits *= 2
        raise Limit("calibration_precision_limit")

    def _query(self, prices, bits, use_elimination=True):
        rows, intervals, pivots, coefficient_bounds = [], [], [], []
        eliminated = []
        last_minor = Q(1)
        exponents = [prices[i] if sign == 0 else -prices[i]
                     for i in range(self.n) for sign in range(2)]
        for j in range(self.rank):
            if use_elimination:
                # c_s = det(previous pivots) * v_s. That common factor
                # cancels from every pivot comparison and normalized row.
                cofactors = self.original[j][:]
                for previous, pivot_column in zip(eliminated, pivots):
                    if cofactors[pivot_column]:
                        factor = cofactors[pivot_column]/previous[pivot_column]
                        cofactors = [v-factor*u if u else v for v, u in zip(cofactors, previous)]
                        self.work.tick(*cofactors, count=4*self.n)
                eliminated.append(cofactors)
            else:
                cofactors = [self.cofactor(j, pivots, s) for s in range(2*self.n)]
            available = [s for s, value in enumerate(cofactors) if value]
            if not available:
                raise ValueError("dependent ordered basis")
            # Squaring removes sqrt(2): every exponent difference is half integral.
            pivot = available[0]
            for s in available[1:]:
                exponent = 2*(exponents[s]-exponents[pivot])
                if scaled_square_greater(cofactors[s]/cofactors[pivot], exponent, self.work):
                    pivot = s
            sign = 1 if use_elimination or last_minor > 0 else -1
            row_intervals = [scaled_interval(sign*value/abs(cofactors[pivot]),
                                            exponents[s]-exponents[pivot], bits, self.work)
                             if value else (Q(0), Q(0)) for s, value in enumerate(cofactors)]
            # Previous pivot coordinates are exactly zero. The new pivot is +/-1.
            bound = Q(1)+sum(max(abs(intervals[k][pivot][0]), abs(intervals[k][pivot][1]))
                             *coefficient_bounds[k] for k in range(j))
            coefficient_bounds.append(bound)
            self.work.tick(bound)
            rows.append([(lo+hi)/2 for lo, hi in row_intervals])
            intervals.append(row_intervals)
            pivots.append(pivot)
            last_minor = cofactors[pivot]
        error = max((hi-lo)/2 for row in intervals for lo, hi in row)
        h = max(coefficient_bounds)
        eps = Q(1, 1024*self.n)
        # This also covers arbitrary feasible auxiliary combinations, whose
        # coefficients satisfy the common H bound, not just true witnesses.
        displacement = self.rank*h*error
        # True normalized circuit witnesses have maximum visible coordinate >=1/2.
        # Bounding displacement certifies membership in B(B) and the 1/4 test.
        if displacement > eps/4:
            return None
        return dict(basis=rows, H=h, epsilon=eps, entry_error=error,
                    coefficient_bounds=coefficient_bounds, displacement_bound=displacement,
                    pivots=pivots, epoch=self.epoch, demand_bound=self.demand_bound,
                    arithmetic_bits=bits, mode="direct_input_height_calibration",
                    dimension_only_complexity=False)
