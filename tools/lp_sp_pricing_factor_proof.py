"""Construct and independently check an implicit exact dual certificate."""
import argparse
import ctypes
import json
import math
from pathlib import Path
import sys
import time
import numpy as np
from scipy import sparse
from lp_sp_pricing_budget import ROOT, BASE, binding, put
from lp_billion_arrays import read as read_array, write
from lp_sp_pricing_scale_verify import vector
sys.path.insert(0, str(ROOT/'research/lp-sp-pricing/python'))
from sp_pricing.geometry_fast import dyadic_integers
from sp_pricing.factor_projection import inverse_proposal
from sp_pricing.implicit_certificate import inverse_bound, correction_bound, up


def exact_primal_proposal(a, b, c, x):
    encoded = dyadic_integers([a.data, b, c])
    if encoded is None:
        return None
    exponent, (av, bv, cv) = encoded
    ai = sparse.csr_matrix((av, a.indices, a.indptr), shape=a.shape)
    maximum_a = max(abs(int(av.min(initial=0))), abs(int(av.max(initial=0))))
    maximum_b = max(abs(int(bv.min(initial=0))), abs(int(bv.max(initial=0))))
    degree = int(np.diff(a.indptr).max(initial=0))
    for px in range(25):
        q = np.rint(np.ldexp(x, px))
        if not np.isfinite(q).all() or np.max(np.abs(q), initial=0) > 2**40:
            break
        xi = q.astype(np.int64)
        bound = maximum_a*int(np.max(np.abs(xi), initial=0))*degree+maximum_b*(1 << px)
        if bound >= 1 << 62:
            continue
        lhs = ai@xi; rhs = bv*(1 << px)
        active = lhs == rhs
        if np.all(lhs <= rhs) and np.count_nonzero(active) >= a.shape[1]:
            return np.ldexp(xi.astype(float), -px), active, px
    return None


def build(a, b, c, x, y, gpu=False):
    start = time.perf_counter_ns(); primal = exact_primal_proposal(a, b, c, x)
    if primal is None:
        return None, dict(reason='no_exact_active_primal', elapsed_ns=time.perf_counter_ns()-start)
    xp, active, px = primal; n = a.shape[1]
    py = 48; rounded = np.rint(np.ldexp(np.maximum(y, 0.), py))
    if not np.isfinite(rounded).all() or np.max(rounded, initial=0) > 2**52:
        return None, dict(reason='dual_base_range')
    y0 = np.ldexp(rounded, -py); y0[~active] = 0.
    available = np.flatnonzero(active & (y0 > 0))
    if len(available) < n:
        return None, dict(reason='insufficient_positive_active_rows')
    selections = [available[np.argsort(-y0[available], kind='stable')[:n]],
                  available[np.linspace(0, len(available)-1, n, dtype=int)]]
    attempts = []
    for selected in selections:
        bt = a[selected].toarray().T
        try:
            r = inverse_proposal(bt, gpu=gpu)
            bound = inverse_bound(bt, r)
        except (ArithmeticError, ValueError, np.linalg.LinAlgError) as error:
            attempts.append(dict(reason=str(error))); continue
        attempts.append(bound)
        if bound['accepted']:
            # The builder does not accept the LP. The independent checker must
            # recompute the exact residual and establish dual nonnegativity.
            return dict(x=xp, y0=y0, basis=selected.astype(np.uint32), inverse=r), dict(
                method='implicit_active_basis_dual_correction', gpu_inverse=gpu,
                primal_exponent=px, dual_base_exponent=py, active_rows=int(active.sum()),
                basis_rows=n, inverse_entries=n*n, explicit_rational_nullspace_entries=0,
                attempts=attempts, elapsed_ns=time.perf_counter_ns()-start)
    return None, dict(reason='inverse_proposal_failed', attempts=attempts, elapsed_ns=time.perf_counter_ns()-start)


def verify_arrays(offsets, indices, values, b, c, x, y0, basis, inverse, seconds=120):
    start = time.perf_counter_ns(); deadline = time.monotonic()+seconds
    if ctypes.CDLL(None).fegetround() != 0:
        return dict(accepted=False, reason='non_nearest_CPU_rounding')
    m, n = len(b), len(c); basis = np.asarray(basis)
    if (len(x) != n or len(y0) != m or len(offsets) != m+1 or int(offsets[0]) != 0
            or int(offsets[-1]) != len(values) or len(indices) != len(values)
            or basis.shape != (n,) or basis.dtype.kind not in 'iu'
            or len(np.unique(basis)) != n or (n and (int(basis.min()) < 0 or int(basis.max()) >= m))):
        return dict(accepted=False, reason='dimensions_or_basis')
    xi, dx = vector(list(map(float, x))); yi, dy = vector(list(map(float, y0)))
    if any(v < 0 for v in yi):
        return dict(accepted=False, reason='negative_dual_base')
    denominator = 1; cache = {}
    for array in (values, b, c):
        for first in range(0, len(array), 65536):
            for raw in np.unique(array[first:first+65536]):
                value = float(raw)
                if not math.isfinite(value):
                    return dict(accepted=False, reason='nonfinite_original_model')
                numerator, den = value.as_integer_ratio(); denominator = max(denominator, den)
            if time.monotonic() > deadline: raise TimeoutError('implicit proof deadline')
    if denominator.bit_length() > 53 or dx.bit_length() > 53 or dy.bit_length() > 53:
        return dict(accepted=False, reason='implicit_proof_dyadic_resource_limit')
    def integer(raw):
        value = float(raw)
        if value in cache: return cache[value]
        num, den = value.as_integer_ratio(); answer = num*(denominator//den)
        if len(cache) < 8192: cache[value] = answer
        return answer
    # Cache matrix alphabet first; RHS/objective diversity cannot evict it.
    for first in range(0, len(values), 65536):
        for value in np.unique(values[first:first+65536]): integer(value)
    bi = list(map(integer, b)); ci = list(map(integer, c))
    dual = [0]*n; active = np.zeros(m, dtype=bool); feasible = support = True; visited = 0
    for i in range(m):
        begin, end = int(offsets[i]), int(offsets[i+1])
        if not 0 <= begin <= end <= len(values): return dict(accepted=False, reason='offsets')
        total = 0; previous = -1
        for k in range(begin, end):
            j = int(indices[k])
            if not previous < j < n: return dict(accepted=False, reason='noncanonical_CSR')
            previous = j; coefficient = integer(values[k])
            total += coefficient*xi[j]; dual[j] += coefficient*yi[i]
        slack = bi[i]*dx-total; feasible = feasible and slack >= 0; active[i] = slack == 0
        support = support and (yi[i] == 0 or slack == 0); visited += end-begin
        if i % 64 == 0 and time.monotonic() > deadline: raise TimeoutError('implicit proof deadline')
    if not feasible or not support or not np.all(active[basis.astype(np.int64)]):
        return dict(accepted=False, reason='primal_or_complementarity', primal_feasible=feasible,
                    supported_on_exactly_active_rows=support, visited_nonzeros=visited)
    residual = max((abs(q*dy-v) for q, v in zip(ci, dual)), default=0)
    exponent = denominator.bit_length()+dy.bit_length()-2
    residual_upper = 0. if not residual else up(max(math.ldexp(up(float(residual)), -exponent), np.finfo(float).tiny))
    a = sparse.csr_matrix((values, indices, offsets), shape=(m, n))
    proof = inverse_bound(a[basis.astype(np.int64)].toarray().T, inverse)
    delta = correction_bound(proof['inverse_norm_upper'], residual_upper) if proof['accepted'] else math.inf
    minimum = float(np.min(np.asarray(y0)[basis.astype(np.int64)], initial=math.inf))
    accepted = bool(proof['accepted'] and minimum >= delta)
    return dict(accepted=accepted, kind='rigorous_implicit_exact_dual', primal_feasible=feasible,
        supported_on_exactly_active_rows=support, dual_stationarity='exact by the defined nonsingular solve',
        zero_gap='exact by complementarity', inverse_proof=proof, residual_numerator=str(residual),
        residual_denominator_exponent=exponent, residual_upper=residual_upper,
        correction_infinity_upper=delta if math.isfinite(delta) else None,
        minimum_selected_dual_base=minimum, visited_nonzeros=visited, rows=m, columns=n,
        elapsed_ns=time.perf_counter_ns()-start,
        proof_definition='y=y0+E_basis*delta; B.T*delta=c-A.T*y0; all other y entries unchanged')


def check(model, certificate, seconds=120):
    start = time.perf_counter_ns(); raw = json.loads(Path(model).read_text()); cert = json.loads(Path(certificate).read_text())
    arrays = {k:read_array(BASE, v) for k, v in raw['arrays'].items()}
    if raw['sense'] != 'maximize' or raw['offset'] != 0 or not (np.isneginf(arrays['column_lower']).all()
            and np.isposinf(arrays['column_upper']).all() and np.isneginf(arrays['row_lower']).all()):
        raise ValueError('canonical original model required')
    n = raw['columns']; m = raw['rows']; oi = arrays['objective_indices']
    if (raw.get('schema_version') != 1 or raw['nonzeros'] != len(arrays['values'])
            or len(arrays['row_upper']) != m or len(arrays['row_lower']) != m
            or len(arrays['column_lower']) != n or len(arrays['column_upper']) != n
            or len(oi) != len(arrays['objective_values'])):
        raise ValueError('original model dimensions')
    if len(oi) and (int(oi[-1]) >= n or np.any(oi[1:] <= oi[:-1])): raise ValueError('objective indices')
    c = np.zeros(n); c[oi] = arrays['objective_values']; data = cert['implicit_certificate']
    result = verify_arrays(arrays['offsets'], arrays['indices'], arrays['values'], arrays['row_upper'], c,
        read_array(BASE, data['primal']), read_array(BASE, data['dual_base']), read_array(BASE, data['basis']),
        read_array(BASE, data['inverse']).reshape(n, n), seconds)
    result.update(complete_ns=time.perf_counter_ns()-start, model=binding(model), certificate=binding(certificate))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('model', type=Path); p.add_argument('certificate', type=Path)
    p.add_argument('output', type=Path); args = p.parse_args(); put(args.output, check(args.model, args.certificate))
