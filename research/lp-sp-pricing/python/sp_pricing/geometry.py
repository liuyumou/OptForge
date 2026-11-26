"""Original slack spaces, bounded auxiliary LPs, and exact label witnesses."""
from fractions import Fraction as Q
from .exact import basis, nullspace, transpose, dot, solve, rational, Limit
from .lp import certificate, free, check


def slack_space(a, b, work, columns=None):
    n = len(a[0]) if a else (columns or 0)
    generators = [[-v for v in col]+[Q(0)] for col in transpose(a, n)]
    generators.append(list(b)+[Q(1)])
    return basis(generators, work)


def paired_space(c, work, dimension=None):
    n = len(c[0]) if c else dimension
    if n is None or n < 1:
        raise ValueError("positive ambient dimension required")
    positive = basis(c, work)
    negative = nullspace(positive, work, n)
    result = []
    for h, rows in ((1, positive), (-1, negative)):
        for row in rows:
            result.append([row[i] if slot == int(h > 0) else Q(0)
                           for i in range(n) for slot in range(2)])
    return result


def restrict_space(c, coordinates, work, dimension=None):
    n = len(c[0]) if c else dimension
    if not c:
        return []
    constraints = [[row[j] for row in c] for j in coordinates]
    coefficients = nullspace(constraints, work, len(c))
    return basis([[dot(v, col, work) for col in transpose(c, n)] for v in coefficients], work)


class LabelOracle:
    """A batch shares B and constraints. Every accepted label has an exact proof.

    The calibration producer is responsible for the visibility/common-demand
    theorem. This class proves the stated tests on the supplied rational B.
    """
    def __init__(self, b, h, epsilon, work, epoch=0, isotropic_error=None):
        self.b = [list(map(rational, row)) for row in b]
        if not b or not b[0] or len(b[0]) % 2 or any(len(row) != len(b[0]) for row in b):
            raise ValueError("paired nonempty basis required")
        self.n, self.r = len(b[0])//2, len(b)
        self.h, self.epsilon, self.work, self.epoch = rational(h), rational(epsilon), work, epoch
        if self.h <= 0 or not 0 < self.epsilon < Q(1, 4):
            raise ValueError("invalid auxiliary bounds")
        self.columns = transpose(self.b)
        self.row_entries = [[(j, v) for j, v in enumerate(row) if v] for row in self.b]
        self.column_entries = [[(j, v) for j, v in enumerate(col) if v] for col in self.columns]
        self.a, self.rhs = [], []
        for j in range(self.r):
            row = [Q(int(i == j)) for i in range(self.r)]
            self.a.extend([row, [-v for v in row]])
            self.rhs.extend([self.h, self.h])
        for col in self.columns:
            self.a.extend([col, [-v for v in col]])
            self.rhs.extend([Q(2), self.epsilon])
        # Independently bound Q(xi B) for all |xi| <= H. Exact isotropic
        # spaces produce zero even when H is large; no guessed numerical zero.
        if isotropic_error is not None:
            # The paired-space calibration proves an isotropic B* with
            # ||xi(B-B*)||inf <= delta. For FEASIBLE y=xiB, |y_s|<=2,
            # |Q(y)-Q(y*)| <= N*delta*(4+delta). No Gram product is needed.
            delta=rational(isotropic_error)
            if delta<0:raise ValueError('negative calibration displacement')
            self.q_bound=self.n*delta*(4+delta)
        else:
            gram = {}
            for k in range(self.n):
                for i, left in self.column_entries[2*k]:
                    for j, right in self.column_entries[2*k+1]:
                        product = left*right/2
                        gram[i, j] = gram.get((i, j), Q(0))+product
                        gram[j, i] = gram.get((j, i), Q(0))+product
                        work.tick(gram[i, j], gram[j, i], count=4)
            gram_sum = sum(map(abs, gram.values()), Q(0))
            self.q_bound = self.h*self.h*gram_sum
        lower = ((Q(1, 4)-self.epsilon)/2)**2-2*(self.n-1)*self.epsilon
        self.broadcast_negative = self.q_bound < lower
        self.calls = 0

    def witness(self, xi):
        xi = list(map(rational, xi))
        if len(xi) != self.r or any(abs(v)>self.h for v in xi):
            raise ValueError("uncertified auxiliary witness")
        y = self.multiply(xi)
        if any(v < -self.epsilon or v > 2 for v in y):
            raise ValueError("uncertified auxiliary witness")
        return y

    def multiply(self, xi):
        if len(xi) != self.r:
            raise ValueError("auxiliary coefficient dimension")
        result = []
        for entries in self.column_entries:
            value = sum((v*xi[j] for j, v in entries if xi[j]), Q(0))
            self.work.tick(value, count=2*len(entries))
            result.append(value)
        return result

    def residual(self, target, dual):
        if len(dual) != 2*self.n:
            raise ValueError("auxiliary dual dimension")
        result = []
        for row, entries in zip(self.b, self.row_entries):
            value = row[2*target+1]-sum((v*dual[j] for j, v in entries if dual[j]), Q(0))
            self.work.tick(value, count=2*len(entries))
            result.append(value)
        return result

    def labels(self, batch_width=32, broadcast=True, expected_epoch=None, gpu=None):
        from contextlib import ExitStack
        from .native_auxiliary import NativeAuxiliary,LIBRARY
        with ExitStack() as stack:
            def native_factory():
                return stack.enter_context(NativeAuxiliary(self.a,self.rhs,self.work)) if LIBRARY.exists() else None
            return self._labels(batch_width,broadcast,expected_epoch,gpu,native_factory)

    def _labels(self,batch_width,broadcast,expected_epoch,gpu,native_factory):
        if expected_epoch is not None and expected_epoch != self.epoch:
            raise ValueError("stale calibration epoch")
        if batch_width not in (1, 8, 32, 64):
            raise ValueError("unadmitted batch width")
        labels, proofs = {}, []
        shared_tableau = {}
        self.gpu_metadata = None
        if gpu is not None:
            from .gpu import propose_labels
            labels, proofs, self.gpu_metadata = propose_labels(self, width=batch_width, **gpu)
        native=native_factory() if len(labels)<self.n else None
        for start in range(0, self.n, batch_width):
            batch = [i for i in range(start, min(start+batch_width, self.n)) if i not in labels]
            for i in batch:
                if i in labels:
                    continue
                objective=self.columns[2*i+1]
                result = native.solve(objective) if native is not None else free(
                    self.a, self.rhs, objective, self.work,state=shared_tableau,target=Q(1,4))
                self.calls += 1
                if result["status"] not in ("optimal","feasible_target"):
                    raise ArithmeticError("bounded label LP should be feasible and bounded")
                y = self.witness(result["x"])
                if result['status']=='optimal':check(self.a,self.rhs,objective,result)
                elif result['value']<Q(1,4) or y[2*i+1]!=result['value']:
                    raise ArithmeticError('early auxiliary target not proved')
                result.setdefault('oracle','exact_shared_tableau_with_target_exit')
                targets = range(self.n) if broadcast else (i,)
                established = {}
                for j in targets:
                    if y[2*j+1] >= Q(1, 4):
                        established[j] = 1
                    elif broadcast and self.broadcast_negative and y[2*j] >= Q(1, 4):
                        established[j] = -1
                # At equality a feasible witness establishes +. A timeout or
                # an approximate objective never establishes a negative label.
                established[i] = 1 if result["value"] >= Q(1, 4) else -1
                if any(j in labels and labels[j] != h for j, h in established.items()):
                    raise ArithmeticError("contradictory exact labels")
                labels.update(established)
                proofs.append(dict(target=i, certificate=result, witness=y,
                                   established=established, epoch=self.epoch))
        return [labels[i] for i in range(self.n)], proofs


def circuit_from_support(c, target, support, work):
    """Recover and exactly verify a candidate line; never guess a circuit."""
    n = len(c[0]) if c else 0
    if not 0 <= target < n or target not in support:
        return None
    restricted = restrict_space(c, [j for j in range(n) if j not in support], work)
    if len(restricted) != 1 or restricted[0][target] == 0:
        return None
    v = [x/restricted[0][target] for x in restricted[0]]
    if any(x < 0 for x in v):
        return None
    return v


def recover_slack_certificate(a, b, side, vector, work, columns=None):
    n = len(a[0]) if a else (columns or 0)
    if len(vector) != len(b)+1 or vector[-1] <= 0 or any(v < 0 for v in vector):
        raise ValueError("invalid original-space witness")
    if side == 1:
        rhs = [bi-vi/vector[-1] for bi, vi in zip(b, vector)]
        x = solve(a, rhs, work, n)
        if x is None or any(dot(row, x, work) > bi for row, bi in zip(a, b)):
            raise ArithmeticError("primal reconstruction failed")
        return dict(status="feasible", x=x)
    y = vector[:-1]
    if any(dot(col, y, work) for col in transpose(a, n)) or dot(b, y, work) >= 0:
        raise ArithmeticError("Farkas reconstruction failed")
    return dict(status="infeasible", y=y)
