"""Bounded exact auxiliary solver, explicitly identified as rational simplex.

This is a practical oracle and a test oracle, not the paper's bit-polynomial
ellipsoid implementation. Every externally consumed result carries an exact
primal/dual, Farkas, or improving-ray witness.
"""
from fractions import Fraction as Q
from .exact import Limit, dot, rational, transpose


def standard(a, b, c, work, pivot_limit=4096, state=None, target=None):
    """Max c*x, A*x <= b, x >= 0; deterministic two-phase exact tableau."""
    m, n = len(b), len(c)
    if len(a) != m or any(len(row) != n for row in a):
        raise ValueError("LP dimensions")
    if (m+2)*(n+2) > 1_000_000:
        raise Limit("tableau_entry_limit")
    d = [[Q(0)]*(n+2) for _ in range(m+2)]
    basic, nonbasic = list(range(n, n+m)), list(range(n))+[-1]
    for i in range(m):
        d[i][:n] = map(rational, a[i])
        d[i][n], d[i][n+1] = Q(-1), rational(b[i])
    d[m][:n] = [-rational(v) for v in c]
    d[m+1][n] = Q(1)
    reused = bool(state and state.get('ready'))
    if reused:
        if state['shape'] != (m,n):
            raise ValueError('shared tableau shape changed')
        d,basic,nonbasic=state['d'],state['basic'],state['nonbasic']
        d[m]=[-rational(c[v]) if 0<=v<n else Q(0) for v in nonbasic]+[Q(0)]
        for i,v in enumerate(basic):
            if 0<=v<n and c[v]:
                for j in range(n+2):
                    if d[i][j]:d[m][j]+=c[v]*d[i][j]
        work.tick(*d[m],count=(n+2)*m)
    pivots = 0

    def pivot(r, s):
        nonlocal pivots
        pivots += 1
        if pivots > pivot_limit:
            raise Limit("simplex_pivot_limit")
        inv = 1/d[r][s]
        nonzero = [j for j in range(n+2) if j != s and d[r][j]]
        for i in range(m+2):
            if i == r or not d[i][s]:
                continue
            factor = d[i][s]*inv
            for j in nonzero:
                d[i][j] -= d[r][j]*factor
                work.tick(d[i][j], count=2)
        for j in nonzero:
            d[r][j] *= inv
        for i in range(m+2):
            if i != r:
                d[i][s] *= -inv
        d[r][s] = inv
        basic[r], nonbasic[s] = nonbasic[s], basic[r]

    def dual_row(objective):
        # Slack reduced costs are the original-row dual multipliers. Basic
        # slacks have zero reduced cost; the artificial column is excluded.
        y = [Q(0)]*m
        for j, variable in enumerate(nonbasic):
            if n <= variable < n+m:
                y[variable-n] = d[objective][j]
        return y

    def iterate(phase):
        objective = m+1 if phase == 1 else m
        while True:
            if phase==2 and target is not None and d[m][n+1]>=target:
                return 'target'
            choices = [j for j in range(n+1) if not (phase == 2 and nonbasic[j] == -1)
                       and d[objective][j] < 0]
            if not choices:
                return None
            # Bland's rule: bounded execution and deterministic handling of degeneracy.
            s = min(choices, key=lambda j: nonbasic[j])
            rows = [i for i in range(m) if d[i][s] > 0]
            if not rows:
                return s
            r = min(rows, key=lambda i: (d[i][n+1]/d[i][s], basic[i]))
            pivot(r, s)

    if m and not reused:
        r = min(range(m), key=lambda i: (d[i][n+1], basic[i]))
        if d[r][n+1] < 0:
            pivot(r, n)
            if iterate(1) is not None or d[m+1][n+1] != 0:
                return dict(status="infeasible", pivots=pivots, y=dual_row(m+1))
            for r in range(m):
                if basic[r] == -1:
                    choices = [j for j in range(n+1) if nonbasic[j] != -1 and d[r][j]]
                    if choices:
                        pivot(r, min(choices, key=lambda j: nonbasic[j]))
    if state is not None:
        state.update(ready=True,shape=(m,n),d=d,basic=basic,nonbasic=nonbasic)
    entering = iterate(2)
    x = [Q(0)]*n
    for i in range(m):
        if 0 <= basic[i] < n:
            x[basic[i]] = d[i][n+1]
    if entering == 'target':
        return dict(status='feasible_target',x=x,value=dot(c,x,work),pivots=pivots)
    if entering is not None:
        ray = [Q(0)]*n
        if 0 <= nonbasic[entering] < n:
            ray[nonbasic[entering]] = Q(1)
        for i in range(m):
            if 0 <= basic[i] < n:
                ray[basic[i]] = -d[i][entering]
        return dict(status="unbounded", x=x, ray=ray, pivots=pivots)
    return dict(status="optimal", x=x, y=dual_row(m), value=dot(c, x, work), pivots=pivots)


def free(a, b, c, work, state=None, target=None):
    n = len(c)
    result = standard([list(row)+[-v for v in row] for row in a], b,
                      list(c)+[-v for v in c], work, state=state, target=target)
    for key in ("x", "ray"):
        if key in result:
            result[key] = [result[key][i]-result[key][n+i] for i in range(n)]
    return result


def certificate(a, b, c, work, lexicographic=False):
    """Free-variable LP with exact witnesses; no tolerances or inferred failures."""
    a = [list(map(rational, row)) for row in a]
    b, c = list(map(rational, b)), list(map(rational, c))
    result = free(a, b, c, work)
    n = len(c)
    if result["status"] == "optimal":
        value = result["value"]
        if lexicographic:
            rows = [*a, c, [-v for v in c]]
            bounds = [*b, value, -value]
            for i in range(n):
                objective = [Q(-int(j == i)) for j in range(n)]
                part = free(rows, bounds, objective, work)
                if part["status"] != "optimal":
                    raise Limit("unbounded_lexicographic_face")
                result["x"] = part["x"]
                coordinate = [Q(int(j == i)) for j in range(n)]
                rows += [coordinate, [-v for v in coordinate]]
                bounds += [part["x"][i], -part["x"][i]]
    result["oracle"] = "exact_rational_simplex_bland"
    check(a, b, c, result)
    return result


def check(a, b, c, result):
    """Internal consistency check; external checker has an independent parser."""
    status = result["status"]
    if status in ("optimal", "unbounded"):
        x = result["x"]
        if len(x) != len(c) or any(dot(row, x) > rhs for row, rhs in zip(a, b)):
            raise ArithmeticError("invalid primal witness")
    if status in ("optimal", "infeasible"):
        y = result["y"]
        target = c if status == "optimal" else [Q(0)]*len(c)
        if len(y) != len(b) or any(v < 0 for v in y):
            raise ArithmeticError("invalid dual signs")
        if any(dot(col, y) != v for col, v in zip(transpose(a, len(c)), target)):
            raise ArithmeticError("invalid dual equations")
        if status == "optimal" and dot(b, y) != dot(c, result["x"]):
            raise ArithmeticError("nonzero exact gap")
        if status == "infeasible" and dot(b, y) >= 0:
            raise ArithmeticError("invalid Farkas inequality")
    if status == "unbounded":
        ray = result["ray"]
        if len(ray) != len(c) or any(dot(row, ray) > 0 for row in a) or dot(c, ray) <= 0:
            raise ArithmeticError("invalid improving ray")
    if status not in ("optimal", "infeasible", "unbounded"):
        raise ValueError("non-certificate status")
