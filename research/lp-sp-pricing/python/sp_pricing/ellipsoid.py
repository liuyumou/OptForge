"""Bounded rational ellipsoid oracle for integer well-described polyhedra.

Separation must return an INTEGER inequality violated by more than delta, or
certify that every inequality is satisfied within delta. Facet coefficient and
coordinate bounds are part of the interface, not inferred from observed cuts.

Exact feasibility follows from an integer Farkas/vertex gap bound. Central cuts
use rational enclosing centers, outward matrix rounding and explicit volume
allowances. Lexicographic optima are reconstructed within the original vertex
denominator bound. Resource refusals never assert infeasibility.
"""
from fractions import Fraction as Q
import math
from .exact import dot, rational, Limit
from .calibration import floor_log2, sqrt_interval
from .compression import bounded_power


class Polytope:
    def __init__(self, dimension, bound, coefficient_bound, separate):
        if dimension < 1 or type(bound) is not int or bound < 1 or type(coefficient_bound) is not int or coefficient_bound < 1:
            raise ValueError("integer polytope bounds")
        self.n, self.bound, self.coefficient_bound = dimension, bound, coefficient_bound
        self.separator = separate

    def separate(self, point, delta):
        for i, value in enumerate(point):
            if abs(value)>self.bound+delta:
                sign = 1 if value>0 else -1
                return [sign*int(j==i) for j in range(self.n)], self.bound
        return self.separator(point, delta)

    def append(self, constraints):
        base = self
        constraints = [(list(map(int, a)), int(b)) for a, b in constraints]
        bound = max([self.coefficient_bound]+[abs(v) for a, _ in constraints for v in a])
        def separate(point, delta):
            cut = base.separate(point, delta)
            if cut is not None:
                return cut
            return next(((a, b) for a, b in constraints if dot(a, point)-b>delta), None)
        return Polytope(self.n, self.bound, bound, separate)


def explicit(a, b, bound):
    if not a or len(a)!=len(b) or not a[0] or any(len(row)!=len(a[0]) for row in a):
        raise ValueError("nonempty explicit polytope dimensions")
    rows = []
    for row, rhs in zip(a, b):
        values = [*map(rational, row), rational(rhs)]
        scale = math.lcm(*(v.denominator for v in values))
        integers = [int(v*scale) for v in values]
        divisor = math.gcd(*integers) or 1
        rows.append(([v//divisor for v in integers[:-1]], integers[-1]//divisor))
    magnitude = max(1, *(abs(v) for row, _ in rows for v in row))
    def separate(point, delta):
        return next(((row, rhs) for row, rhs in rows if dot(row, point)-rhs>delta), None)
    return Polytope(len(a[0]), bound, magnitude, separate)


def feasible(poly, work):
    """Decide exact feasibility; a returned relaxed point is not an LP witness."""
    n, bound, magnitude = poly.n, poly.bound, poly.coefficient_bound
    determinant_bound = math.factorial(n+1)*bounded_power(magnitude+1, n+1, work)
    delta = Q(1, 4*determinant_bound)
    radius = Q(n*(bound+1))
    inner = delta/(n*magnitude)
    logarithm = max(1, floor_log2(radius/inner)+2)
    iterations = 8*n*(n+1)*logarithm
    center = [Q(0)]*n
    if n == 1:
        lo, hi = -radius, radius
        for step in range(iterations):
            center = [(lo+hi)/2]
            cut = poly.separate(center, delta)
            work.tick(*center)
            if cut is None:
                return dict(feasible=True, relaxed_point=center, delta=delta, iterations=step)
            a, b = checked_cut(poly, center, delta, cut)
            if not a[0]:
                return dict(feasible=False, iterations=step+1)
            if a[0]>0:
                hi=center[0]
            else:
                lo=center[0]
        return dict(feasible=False, iterations=iterations)
    # lambda_min after k central cuts is >= radius^2 * 4^-k. Global grids
    # keep both matrix error and center error below kappa in that metric.
    kappa = Q(1, 100*n*n)
    center_bits = iterations+(400*n**3).bit_length()+4
    matrix_bits = 2*iterations+(800*n**3).bit_length()+4
    if 4*matrix_bits+64 > work.max_bits:
        raise Limit("ellipsoid_rounding_bit_admission")
    center_grid = work.power2(-center_bits)
    matrix_grid = work.power2(-matrix_bits)
    shape = [[radius*radius*int(i==j) for j in range(n)] for i in range(n)]
    inflation = (1+kappa)**4
    for step in range(iterations):
        work.tick()
        cut = poly.separate(center, delta)
        if cut is None:
            return dict(feasible=True, relaxed_point=center, delta=delta, iterations=step)
        a, b = checked_cut(poly, center, delta, cut)
        if not any(a):
            return dict(feasible=False, iterations=step+1)
        direction = [dot(row, a, work) for row in shape]
        squared = dot(a, direction, work)
        if squared<=0:
            raise ArithmeticError("ellipsoid lost positive definiteness")
        precision = max(0, -floor_log2(squared)//2)+(1000*n*n).bit_length()+8
        lower, upper = sqrt_interval(squared, precision, work)
        if lower<=0 or upper/lower>1+kappa:
            raise ArithmeticError("ellipsoid square-root enclosure")
        center = [x-v/((n+1)*upper) for x, v in zip(center, direction)]
        center = [(v/center_grid).__floor__()*center_grid for v in center]
        factor = Q(n*n, n*n-1)*inflation
        shape = [[factor*(shape[i][j]-Q(2,n+1)*direction[i]*direction[j]/squared)
                  for j in range(n)] for i in range(n)]
        shape = [[(shape[i][j]/matrix_grid).__floor__()*matrix_grid+n*matrix_grid*int(i==j)
                  for j in range(n)] for i in range(n)]
        work.tick(*center, *(v for row in shape for v in row), count=n*n)
    # Each step shrinks volume by at least exp(-1/(4(n+1))). If the original
    # polytope were nonempty, its delta relaxation would contain the inner ball.
    return dict(feasible=False, iterations=iterations)


def checked_cut(poly, point, delta, cut):
    a, b = cut
    if len(a)!=poly.n or type(b) is not int or any(type(v) is not int for v in a):
        raise ValueError("ellipsoid separator must return integer coefficients")
    if any(abs(v)>poly.coefficient_bound for v in a):
        raise ValueError("ellipsoid coefficient bound violated")
    if dot(a, point)-b<=delta:
        raise ValueError("ellipsoid separator did not return a violated cut")
    return a, b


def lex_minimize(poly, work, order=None):
    """Exact coordinate optimization over a bounded rational polytope."""
    n = poly.n
    order = list(range(n)) if order is None else list(order)
    if sorted(order)!=list(range(n)):
        raise ValueError("coordinate permutation required")
    original_denominator = math.factorial(n)*bounded_power(poly.coefficient_bound, n, work)
    resolution = Q(1, 8*original_denominator**2)
    if not feasible(poly, work)["feasible"]:
        return dict(status="infeasible", oracle="rational_rounded_ellipsoid")
    face, point, decisions = poly, [Q(0)]*n, 1
    for coordinate in order:
        lo, hi = Q(-poly.bound), Q(poly.bound)
        while hi-lo>resolution:
            middle = (lo+hi)/2
            row = [middle.denominator*int(i==coordinate) for i in range(n)]
            candidate = face.append([(row, middle.numerator)])
            decision = feasible(candidate, work)
            decisions += 1
            if decision["feasible"]:
                hi=middle
            else:
                lo=middle
        value = ((lo+hi)/2).limit_denominator(original_denominator)
        if not lo<=value<=hi:
            raise ArithmeticError("ellipsoid rational reconstruction interval")
        point[coordinate]=value
        row = [value.denominator*int(i==coordinate) for i in range(n)]
        face=face.append([(row,value.numerator),([-v for v in row],-value.numerator)])
        work.tick(value)
    if poly.separate(point,Q(0)) is not None:
        raise ArithmeticError("reconstructed vertex failed exact separation")
    return dict(status="optimal", x=point, feasibility_decisions=decisions,
                oracle="rational_rounded_ellipsoid", vertex_denominator_bound=original_denominator)


def lex_minimize_lattice(poly,work,denominators,order=None):
    """Optimize when the caller proves all vertex coordinates lie on these grids.

    The implicit-market half-integrality theorem supplies that proof. This
    specialized entry point is not used for arbitrary rational polyhedra.
    """
    if len(denominators)!=poly.n or any(type(d) is not int or d<1 for d in denominators):
        raise ValueError('positive integer vertex grids required')
    order=list(range(poly.n)) if order is None else list(order)
    if sorted(order)!=list(range(poly.n)):raise ValueError('coordinate permutation required')
    if not feasible(poly,work)['feasible']:return dict(status='infeasible')
    face=poly;point=[Q(0)]*poly.n;decisions=1
    for coordinate in order:
        grid=denominators[coordinate];lo=-poly.bound*grid-1;hi=poly.bound*grid
        row=[grid*int(i==coordinate) for i in range(poly.n)]
        while hi-lo>1:
            middle=(lo+hi)//2
            if feasible(face.append([(row,middle)]),work)['feasible']:hi=middle
            else:lo=middle
            decisions+=1
        point[coordinate]=Q(hi,grid)
        face=face.append([(row,hi),([-v for v in row],-hi)])
    if poly.separate(point,Q(0)) is not None:raise ArithmeticError('vertex-grid recovery failed exact separation')
    return dict(status='optimal',x=point,feasibility_decisions=decisions,oracle='rational_rounded_ellipsoid_vertex_grid')
