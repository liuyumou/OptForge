"""Metadata-only cuOpt observation; retained numerical settings and other adapters."""
from lp_baseline_adapters_v3 import (copt, retained, result, native_status, native_bounds)
from lp_baseline_common_v4 import equal_f64, require, vector, put, ref
from lp_baseline_contract import csr, normalize_original_sense_dual
from lp_baseline_native_policy import observe_solution, diagnostic

def cuopt(model, config, seconds, directory, readback):
    import numpy as np
    from cuopt import linear_programming as lp
    r = result()
    p, i, v = csr(model)
    require(max([len(v), len(p), len(model['variable_ids']), *i], default=0) < 2**31, 'cuOpt int32 index overflow')
    dm = lp.DataModel()
    dm.set_csr_constraint_matrix(np.asarray(v, dtype=np.float64), np.asarray(i, dtype=np.int32), np.asarray(p, dtype=np.int32))
    dm.set_objective_coefficients(np.asarray(model['objective'], dtype=np.float64))
    dm.set_objective_offset(model['offset'])
    dm.set_maximize(model['sense'] == 'maximize')
    bounds = native_bounds(model)
    for key, values in bounds.items():
        getattr(dm, 'set_' + key.replace('row_', 'constraint_') + '_bounds')(np.asarray(values, dtype=np.float64))
    if readback:
        equal_f64(dm.get_constraint_matrix_values(), v)
        require(list(dm.get_constraint_matrix_indices()) == i and list(dm.get_constraint_matrix_offsets()) == p, 'cuOpt CSR readback')
        equal_f64(dm.get_objective_coefficients(), model['objective'])
        equal_f64([dm.get_objective_offset()], [model['offset']])
        require(bool(dm.get_sense()) == (model['sense'] == 'maximize'), 'cuOpt sense readback')
        for key, values in bounds.items(): equal_f64(getattr(dm, 'get_' + key.replace('row_', 'constraint_') + '_bounds')(), values)
        r['readback'] = 'binary64_and_csr_exact'
    settings = lp.SolverSettings()
    parameters = dict(config['parameters'], time_limit=seconds)
    for key, value in parameters.items():
        settings.set_parameter(key, value)
        observed = settings.get_parameter(key)
        require(observed == value, 'cuOpt parameter readback: ' + key)
        r['effective_parameters'][key] = value
    solution = lp.Solve(dm, settings)
    observation = observe_solution(solution, ref(directory/'canonical.json'), parameters)
    # Persist the vendor return before extraction or independent certification can fail.
    observation['original_sha256'] = model['original_sha256']
    returned = put(directory/'vendor-return.json', observation)
    raw_dual = solution.get_dual_solution()
    raw_primal = solution.get_primal_solution()
    vectors = put(directory/'vendor-vectors.json', dict(
        schema_version=1, kind='lp-baseline-native-vectors', native_return=returned,
        primal=None if raw_primal is None else diagnostic(list(raw_primal)),
        dual=None if raw_dual is None else diagnostic(list(raw_dual))))
    r.update(native_return=returned, raw_vectors=vectors,
             native_return_pass=observation['native_return_pass'])
    r.update(primal=vector(raw_primal),
             dual=vector(raw_dual), reduced_costs=vector(solution.get_reduced_cost()),
             native_status=native_status(solution.get_termination_reason()),
             native_solve_ns=round(float(solution.get_solve_time()) * 1e9),
             algorithm_executed=str(solution.get_solved_by()),
             iterations=int(solution.get_lp_stats()['nb_iterations']))
    if r['dual'] is not None:
        r['dual'] = normalize_original_sense_dual(r['dual'], model['sense'])
    r['limitations'].append('GPU execution requires separate affirmative process activity; method selection alone is insufficient.')
    if config['algorithm'] == 'concurrent':
        r['limitations'].append('Concurrent barrier/simplex internal tolerances use native defaults; strict certification remains a separate diagnostic.')
        r['limitations'].append('Presolve-only maximization dual normalization remains unresolved; raw vendor duals are preserved and no vendor-defect attribution is made.')
    return r

