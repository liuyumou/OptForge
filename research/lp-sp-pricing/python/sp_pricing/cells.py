"""Exact fixed-dimensional integer-cell counts and first moments (Section 6.6).

A constraint (i,j,c) means x_i-x_j <= c, with index -1 denoting zero.
Elimination partitions on the first maximizing lower and minimizing upper bound.
Polynomial antiderivatives cover negative endpoints without enumerating guesses.
"""
from fractions import Fraction as Q
from math import comb
from functools import lru_cache


def add(left, right, scale=Q(1)):
    result = left.copy()
    for powers, value in right.items():
        result[powers] = result.get(powers, Q(0))+scale*value
        if not result[powers]:
            del result[powers]
    return result


def power_sums(degree):
    # S_p(n)=sum_{0<=t<n} t^p, as a polynomial valid for every integer n.
    result = []
    for p in range(degree+1):
        coeff = {p+1: Q(1)}
        for j in range(p):
            for k, v in result[j].items():
                coeff[k] = coeff.get(k, Q(0))-comb(p+1, j)*v
        result.append({k: v/Q(p+1) for k, v in coeff.items() if v})
    return result


def substitute(coeff, index, constant, dimensions):
    result = {}
    for p, value in coeff.items():
        for k in range(p+1) if index >= 0 else (0,):
            powers = [0]*dimensions
            if index >= 0:
                powers[index] = k
            coefficient = value*comb(p, k)*constant**(p-k)
            key = tuple(powers)
            result[key] = result.get(key, Q(0))+coefficient
    return {k: v for k, v in result.items() if v}


def canonical(constraints):
    unique = {}
    for i, j, c in constraints:
        if type(c) is not int:
            raise ValueError("integer difference constraints required")
        if i == j:
            if c < 0:
                return None
            continue
        unique[i, j] = min(c, unique.get((i, j), c))
    return [(i, j, c) for (i, j), c in sorted(unique.items())]


@lru_cache(maxsize=16384)
def consistent(dimensions,constraints):
    """Prune contradictory difference cycles before polynomial expansion."""
    size=dimensions+1;zero=dimensions
    distances=[[0 if i==j else None for j in range(size)] for i in range(size)]
    for i,j,c in constraints:
        i=zero if i<0 else i;j=zero if j<0 else j
        previous=distances[i][j]
        distances[i][j]=c if previous is None else min(c,previous)
    for k in range(size):
        for i in range(size):
            if distances[i][k] is None:continue
            for j in range(size):
                if distances[k][j] is None:continue
                candidate=distances[i][k]+distances[k][j]
                if distances[i][j] is None or candidate<distances[i][j]:distances[i][j]=candidate
        if any(distances[i][i]<0 for i in range(size)):return False
    return True


def eliminate(polynomial, dimensions, constraints, work):
    constraints = canonical(constraints)
    if constraints is None or not polynomial:
        return Q(0)
    work.tick(count=(dimensions+1)**3)
    if not consistent(dimensions,tuple(constraints)):return Q(0)
    if dimensions == 0:
        return polynomial.get((), Q(0))
    k = dimensions-1
    lowers, uppers, remaining = [], [], []
    for i, j, c in constraints:
        if i == k:
            uppers.append((j, c))
        elif j == k:
            lowers.append((i, -c))
        else:
            remaining.append((i, j, c))
    if not lowers or not uppers:
        raise ValueError("cell must be bounded")
    sums = power_sums(max(p[-1] for p in polynomial))
    total = Q(0)
    for li, (lindex, lo) in enumerate(lowers):
        for ui, (uindex, hi) in enumerate(uppers):
            branch = remaining+[(lindex, uindex, hi-lo)]
            for j, (index, offset) in enumerate(lowers):
                # First maximum: earlier competing bound must be strictly lower.
                if j != li:
                    branch.append((index, lindex, lo-offset-int(j < li)))
            for j, (index, offset) in enumerate(uppers):
                # First minimum: earlier competing bound must be strictly higher.
                if j != ui:
                    branch.append((uindex, index, offset-hi-int(j < ui)))
            branch=canonical(branch)
            if branch is None or not consistent(k,tuple(branch)):continue
            reduced = {}
            for powers, value in polynomial.items():
                upper = substitute(sums[powers[-1]], uindex, hi+1, k)
                lower = substitute(sums[powers[-1]], lindex, lo, k)
                integrated = add(upper, lower, -1)
                for exponents, coefficient in integrated.items():
                    new = tuple(a+b for a, b in zip(powers[:-1], exponents))
                    reduced[new] = reduced.get(new, Q(0))+value*coefficient
                    work.tick(reduced[new])
            total += eliminate(reduced, k, branch, work)
            work.tick(total)
    return total


def count_and_moments(dimensions, bound, constraints, work):
    if not 0 <= dimensions <= 5 or type(bound) is not int or bound < 0:
        raise ValueError("paper expert cells have at most five guesses")
    if any(not -1 <= i < dimensions or not -1 <= j < dimensions for i, j, _ in constraints):
        raise ValueError("cell index")
    box = [(i, -1, bound) for i in range(dimensions)]+[(-1, i, bound) for i in range(dimensions)]
    constraints = box+list(constraints)
    zero = (0,)*dimensions
    count = eliminate({zero: Q(1)}, dimensions, constraints, work)
    moments = []
    for i in range(dimensions):
        powers = list(zero); powers[i] = 1
        moments.append(eliminate({tuple(powers): Q(1)}, dimensions, constraints, work))
    if count.denominator != 1 or count < 0 or any(v.denominator != 1 for v in moments):
        raise ArithmeticError("cell summation postcondition")
    return dict(count=int(count), sums=[int(v) for v in moments])
