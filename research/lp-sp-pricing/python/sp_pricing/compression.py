"""Exact components of Section 5, with explicit arithmetic admission.

LLL and common-scale extraction operate on rational proxy values. Online requests
invalidate every answer at a restart. The large-log sign-oracle and grouped-market
integration are not supplied by this component; it does not establish a complete
strongly polynomial LP implementation.
"""
from fractions import Fraction as Q
import math
from .exact import dot, Limit, rational


def nearest(value):
    value = rational(value)
    return (2*value.numerator+value.denominator)//(2*value.denominator)


def lll(rows, work, delta=Q(3, 4)):
    """Exact size-reduced lattice basis; no floating-point Lovasz decisions."""
    b = [list(map(int, row)) for row in rows]
    n = len(b)
    if not n or any(len(row) != n for row in b):
        raise ValueError("square full-rank lattice required")
    def gram():
        orthogonal, mu, norms = [], [[Q(0)]*n for _ in range(n)], []
        for i, row in enumerate(b):
            v = list(map(Q, row))
            for j in range(i):
                mu[i][j] = dot(row, orthogonal[j], work)/norms[j]
                v = [x-mu[i][j]*y for x, y in zip(v, orthogonal[j])]
                work.tick(*v)
            norm = dot(v, v, work)
            if not norm:
                raise ValueError("singular lattice")
            orthogonal.append(v); norms.append(norm)
        return mu, norms
    mu, norms = gram()
    k = 1
    while k < n:
        for j in range(k-1, -1, -1):
            q = nearest(mu[k][j])
            if q:
                b[k] = [x-q*y for x, y in zip(b[k], b[j])]
                work.tick(*b[k])
                mu, norms = gram()
        if norms[k] >= (delta-mu[k][k-1]**2)*norms[k-1]:
            k += 1
        else:
            b[k], b[k-1] = b[k-1], b[k]
            mu, norms = gram()
            k = max(1, k-1)
        work.tick()
    return b


def bounded_power(base, exponent, work):
    base = int(base)
    if base < 0 or exponent < 0:
        raise ValueError("nonnegative integer power")
    if base and base.bit_length()*exponent > work.max_bits:
        raise Limit("compression_power_bit_admission")
    answer = base**exponent
    work.tick(answer)
    return answer


def scales(values, epsilon_inverse, threshold, work):
    """Lemma 5.3 for explicit rational proxies, including all postconditions."""
    w = list(map(rational, values)); m = len(w)
    if epsilon_inverse < 2 or threshold < 0:
        raise ValueError("scale parameters")
    eps = Q(1, epsilon_inverse)
    c = int(work.power2(m*(m+1)))*bounded_power(2*epsilon_inverse, m+1, work)
    work.tick(c)
    remainder, result = w[:], []
    while remainder and max(map(abs, remainder)) > threshold:
        if len(result) >= m:
            raise ArithmeticError("scale extraction did not eliminate a coordinate")
        maximum = max(map(abs, remainder))
        denominator = 2*c*epsilon_inverse
        u = [Q(nearest(v/maximum*denominator), denominator) for v in remainder]
        # A common integer scaling of (q*u-z,q/C).
        d = math.lcm(c, *(v.denominator for v in u))
        lattice = [[d*int(i == j) for j in range(m)]+[0] for i in range(m)]
        lattice.append([int(v*d) for v in u]+[d//c])
        short = lll(lattice, work)[0]
        q = Q(short[-1]*c, d)
        if q.denominator != 1 or not q:
            raise ArithmeticError("invalid LLL denominator")
        if q < 0:
            q = -q; short = [-v for v in short]
        digits = [q*v-Q(s, d) for v, s in zip(u, short)]
        if not 1 <= q <= c or any(v.denominator != 1 or abs(v) > c for v in digits):
            raise ArithmeticError("invalid approximation digits")
        scale = maximum/q
        remainder = [v-scale*z for v, z in zip(remainder, digits)]
        if max(map(abs, remainder)) > eps*scale or scale <= Q(threshold, c):
            raise ArithmeticError("common-scale postcondition")
        work.tick(scale, *remainder)
        result.append(dict(scale=scale, digits=[int(v) for v in digits]))
    return dict(C=c, expansion=result, remainder=remainder)


def homogeneous_round(values, norm_bound, work):
    if norm_bound < 1:
        raise ValueError("positive form norm")
    result = scales(values, 2*norm_bound, 0, work)
    base = 2*result["C"]*norm_bound+1
    digits = [0]*len(values)
    for step in result["expansion"]:
        digits = [base*x+y for x, y in zip(digits, step["digits"])]
        work.tick(*digits)
    return digits


class Restart(Exception):
    def __init__(self, epoch):
        super().__init__("compression_restart")
        self.epoch = epoch


class OnlineCompression:
    """Section 5.4 on supplied rational proxies, not an unbounded log oracle."""
    def __init__(self, proxy, norm_bound, eta, dissociation_bound, work):
        self.proxy, self.M, self.eta, self.D, self.work = proxy, norm_bound, rational(eta), dissociation_bound, work
        if self.M < 1 or not 0 < self.eta < 1 or self.D < 1:
            raise ValueError("compression parameters")
        self.indices, self.answers, self.epoch = [], {}, 0
        self.initialize()

    def initialize(self):
        m = len(self.indices)
        epsilon_inverse = 100*(m+1)*self.M
        c = int(self.work.power2(m*(m+1)))*bounded_power(2*epsilon_inverse, m+1, self.work)
        self.H = 100*self.M*c
        self.expansion = scales([self.proxy(i) for i in self.indices], epsilon_inverse, self.H, self.work)
        self.base = 10*self.M*(m*self.H+3)
        self.answers = {}

    def request(self, index):
        if index in self.answers:
            return self.answers[index]
        value = rational(self.proxy(index)); residual = value
        digits, m = [], len(self.indices)
        valid = True
        for step in self.expansion["expansion"]:
            digit = nearest(residual/step["scale"])
            residual -= digit*step["scale"]
            if abs(digit) > m*self.expansion["C"] or abs(residual) > step["scale"]/(10*self.M):
                valid = False
                break
            digits.append(digit)
        valid &= abs(residual) <= m*self.H+2
        if not valid:
            if index in self.indices or len(self.indices)+1 >= self.D:
                raise ArithmeticError("proxy family violated its dissociation promise")
            self.indices.append(index); self.epoch += 1; self.initialize()
            raise Restart(self.epoch)
        grid = (residual/self.eta).__floor__()*self.eta
        answer = grid
        for j, digit in enumerate(digits):
            answer += bounded_power(self.base, len(digits)-j, self.work)*digit
        comparison = grid+sum((s["scale"]*d for s, d in zip(self.expansion["expansion"], digits)), Q(0))
        if abs(comparison-value) > self.eta:
            raise ArithmeticError("compression approximation")
        self.work.tick(answer, comparison)
        result = dict(value=answer, comparison=comparison, epoch=self.epoch, index=index)
        self.answers[index] = result
        return result

    def validate_epoch(self, answer):
        if answer["epoch"] != self.epoch:
            raise ValueError("stale compression answer")
