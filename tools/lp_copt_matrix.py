"""SPEC-0019 exact, dependency-free CSC construction for the optional COPT worker."""
import math
from lp_copt import validate_import_coefficients


def prepare(doc, infinity=1e30):
    """Preserve binary64 inputs; reject ambiguity before any sparse-library coercion."""
    variables = sorted(doc['variables'], key=lambda v: v['id'])
    rows = sorted(doc['constraints'], key=lambda r: r['id'])
    ids = [v['id'] for v in variables]; row_ids = [r['id'] for r in rows]
    if len(set(ids)) != len(ids) or len(set(row_ids)) != len(row_ids):
        raise ValueError('duplicate variable or row ID')
    if any(type(i) is not int or not 0 <= i <= 0xffffffff for i in ids + row_ids):
        raise ValueError('invalid variable or row ID')
    if doc['schema_version'] != 1 or any(v['domain'] != 'continuous' for v in variables):
        raise ValueError('external LP requires version one continuous variables')
    validate_import_coefficients(doc)
    index = {v: i for i, v in enumerate(ids)}

    def bound(b):
        kind = b['kind']
        if kind == 'finite':
            value = b['value']
            if type(value) not in (float, int) or not math.isfinite(value) or abs(value) >= infinity:
                raise ValueError('finite bound exceeds COPT infinity sentinel or is nonfinite')
            return value
        if kind not in ('negative_infinity', 'positive_infinity'):
            raise ValueError('unknown bound kind')
        return infinity if kind == 'positive_infinity' else -infinity

    def bounds(items):
        lo = []; hi = []
        for item in items:
            if item['lower']['kind'] == 'positive_infinity' or item['upper']['kind'] == 'negative_infinity':
                raise ValueError('invalid oriented infinite bound')
            l, u = bound(item['lower']), bound(item['upper'])
            if l > u: raise ValueError('reversed bounds')
            lo.append(l); hi.append(u)
        return lo, hi

    def terms(items):
        seen = set()
        for t in items:
            key = t['variable_id']
            if type(key) is not int or type(t['coefficient']) not in (int, float): raise ValueError('invalid term type')
            if key not in index or key in seen: raise ValueError('duplicate or unknown term variable')
            seen.add(key)
            yield index[key], t['coefficient']

    lb, ub = bounds(variables); lhs, rhs = bounds(rows)
    # Direct column buckets never invoke COO duplicate coalescing or arithmetic.
    columns = [[] for _ in variables]
    for row, item in enumerate(rows):
        for col, value in terms(item['terms']): columns[col].append((row, value))
    pointers = [0]; indices = []; values = []
    for column in columns:
        for row, value in column: indices.append(row); values.append(value)
        pointers.append(len(indices))
    obj = doc['objective']; offset = obj['offset']
    if obj['sense'] not in ('minimize', 'maximize') or not math.isfinite(offset):
        raise ValueError('invalid objective sense/offset')
    costs = [0.0] * len(ids)
    for col, value in terms(obj['terms']): costs[col] = value
    return dict(variable_ids=ids, row_ids=row_ids, indptr=pointers, indices=indices, data=values,
                shape=[len(rows), len(ids)], c=costs, lhs=lhs, rhs=rhs, lb=lb, ub=ub,
                sense=obj['sense'], offset=offset)


def load(cp, model, data, sparse):
    """The only bulk import: no numeric preprocessing or reassessment cache."""
    matrix = sparse.csc_matrix((data['data'], data['indices'], data['indptr']), shape=tuple(data['shape']), dtype='float64')
    model.loadMatrix(data['c'], matrix, data['lhs'], data['rhs'], data['lb'], data['ub'])
    model.setObjSense(cp.COPT.MINIMIZE if data['sense'] == 'minimize' else cp.COPT.MAXIMIZE)
    model.setObjConst(data['offset'])
    if data['variable_ids']: model.setNames(model.getVars(), ['v' + str(i) for i in data['variable_ids']])
    if data['row_ids']: model.setNames(model.getConstrs(), ['r' + str(i) for i in data['row_ids']])
