"""Exact scalar/linear algebra, with explicit finite resource limits."""
from dataclasses import dataclass, field
from fractions import Fraction as Q
import itertools
import math
import re
import time


class Limit(RuntimeError):
    """No mathematical conclusion follows from a resource refusal."""


@dataclass
class Work:
    max_operations: int = 1_000_000
    max_bits: int = 16384
    seconds: float = 30.0
    operations: int = 0
    peak_bits: int = 0
    started: float = field(default_factory=time.monotonic)

    def tick(self, *values, count=1):
        self.operations += count
        for value in values:
            if isinstance(value, Q):
                bits = max(abs(value.numerator).bit_length(), value.denominator.bit_length())
            elif isinstance(value, int):
                bits = abs(value).bit_length()
            else:
                continue
            self.peak_bits = max(self.peak_bits, bits)
        if self.operations > self.max_operations:
            raise Limit("operation_limit")
        if self.peak_bits > self.max_bits:
            raise Limit("arithmetic_bit_limit")
        if time.monotonic() - self.started > self.seconds:
            raise Limit("deadline")

    def power2(self, exponent):
        if abs(exponent)+1 > self.max_bits:
            raise Limit("power_of_two_bit_limit")
        result = Q(1 << exponent) if exponent >= 0 else Q(1, 1 << -exponent)
        self.tick(result)
        return result


def rational(value):
    if isinstance(value, bool):
        raise ValueError("boolean is not an LP coefficient")
    if isinstance(value, dict):
        if set(value) != {"numerator", "denominator"}:
            raise ValueError("invalid rational fields")
        if any(type(v) is not int and (type(v) is not str or re.fullmatch(r"[+-]?[0-9]+", v) is None)
               for v in value.values()):
            raise ValueError("rational fields must be integers")
        return Q(int(value["numerator"]), int(value["denominator"]))
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("nonfinite coefficient")
        return Q.from_float(value)
    return Q(value)


def encode(value):
    if isinstance(value, Q):
        return {"numerator": str(value.numerator), "denominator": str(value.denominator)}
    if isinstance(value, (list, tuple)):
        return [encode(v) for v in value]
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    return value


def dot(a, b, work=None):
    if len(a) != len(b):
        raise ValueError("dot dimension")
    result = Q(0)
    for x, y in zip(a, b):
        if x and y:
            result += x*y
            if work:
                work.tick(result, count=2)
    return result


def transpose(a, columns=None):
    if not a:
        return [[] for _ in range(columns or 0)]
    if any(len(row) != len(a[0]) for row in a):
        raise ValueError("ragged matrix")
    return [list(col) for col in zip(*a)]


def rref(a, work, coefficient_columns=None, use_native=True):
    a = [list(map(rational, row)) for row in a]
    if not a:
        return a, []
    n = len(a[0]) if coefficient_columns is None else coefficient_columns
    if any(len(row) != len(a[0]) for row in a):
        raise ValueError("ragged matrix")
    if use_native and len(a)*len(a[0])>=64:
        from .native_auxiliary import LIBRARY,rref as native_rref
        if LIBRARY.exists():return native_rref(a,work,n)
    pivots = []
    for col in range(n):
        row = next((i for i in range(len(pivots), len(a)) if a[i][col]), None)
        if row is None:
            continue
        at = len(pivots)
        a[at], a[row] = a[row], a[at]
        scale = a[at][col]
        a[at] = [v / scale if v else Q(0) for v in a[at]]
        work.tick(*a[at], count=len(a[at]))
        for i in range(len(a)):
            if i == at or not a[i][col]:
                continue
            scale = a[i][col]
            a[i] = [v-scale*u if u else v for v, u in zip(a[i], a[at])]
            work.tick(*a[i], count=2*len(a[i]))
        pivots.append(col)
        if len(pivots) == len(a):
            break
    return a, pivots


def solve(a, b, work, columns=None):
    n = len(a[0]) if a else (columns or 0)
    if len(a) != len(b):
        raise ValueError("linear system dimension")
    rows, pivots = rref([list(row)+[rational(rhs)] for row, rhs in zip(a, b)], work, n)
    if any(not any(row[:n]) and row[n] for row in rows):
        return None
    x = [Q(0)] * n
    for i, col in enumerate(pivots):
        x[col] = rows[i][n]
    return x


def nullspace(a, work, columns=None):
    n = len(a[0]) if a else (columns or 0)
    rows, pivots = rref(a, work)
    result = []
    for free in range(n):
        if free in pivots:
            continue
        v = [Q(0)] * n
        v[free] = Q(1)
        for i, col in enumerate(pivots):
            v[col] = -rows[i][free]
        result.append(v)
    return result


def basis(a, work):
    rows, pivots = rref(a, work)
    return rows[:len(pivots)]


def determinant(a, work):
    """Exact elimination oracle; the literal Newton route is separate below."""
    n = len(a)
    if any(len(row) != n for row in a):
        raise ValueError("nonsquare minor")
    rows = [list(map(rational, row)) for row in a]
    result = Q(1)
    for col in range(n):
        p = next((i for i in range(col, n) if rows[i][col]), None)
        if p is None:
            return Q(0)
        if p != col:
            rows[p], rows[col] = rows[col], rows[p]
            result = -result
        value = rows[col][col]
        result *= value
        work.tick(result)
        for i in range(col+1, n):
            ratio = rows[i][col]/value
            for j in range(col+1, n):
                rows[i][j] -= ratio*rows[col][j]
                work.tick(rows[i][j], count=2)
    return result


def determinant_newton(a, work):
    """Section 3.4: clear denominators, powers/traces, scaled Newton identities."""
    n = len(a)
    if any(len(row) != n for row in a):
        raise ValueError("nonsquare minor")
    if n == 0:
        return Q(1)
    den = 1
    for row in a:
        for value in row:
            den *= rational(value).denominator
            work.tick(den)
    matrix = [[int(rational(v)*den) for v in row] for row in a]
    power = [[int(i == j) for j in range(n)] for i in range(n)]
    traces = [0]
    for _ in range(n):
        power = [[dot(row, col, work) for col in transpose(matrix)] for row in power]
        traces.append(sum(power[i][i] for i in range(n)))
    coefficients = [Q(1)]
    for i in range(1, n+1):
        value = sum((-1)**(j-1)*math.factorial(i-1)//math.factorial(i-j)
                    *coefficients[i-j]*traces[j] for j in range(1, i+1))
        work.tick(value)
        coefficients.append(value)
    return coefficients[n]/(math.factorial(n)*den**n)


def minor(a, rows, columns, work, literal=False):
    function = determinant_newton if literal else determinant
    return function([[a[i][j] for j in columns] for i in rows], work)


def vertices(a, b, work, max_bases=10000):
    """Independent small bounded-polytope oracle; never called a polynomial solver."""
    n = len(a[0]) if a else 0
    if n == 0:
        if all(rhs >= 0 for rhs in b):
            yield []
        return
    if math.comb(len(a), n) > max_bases:
        raise Limit("enumeration_basis_limit")
    seen = set()
    for indices in itertools.combinations(range(len(a)), n):
        rows = [a[i] for i in indices]
        if determinant(rows, work) == 0:
            continue
        x = solve(rows, [b[i] for i in indices], work)
        if tuple(x) not in seen and all(dot(row, x, work) <= rhs for row, rhs in zip(a, b)):
            seen.add(tuple(x))
            yield x
