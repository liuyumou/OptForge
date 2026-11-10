"""Versioned scalar COPT, cuOpt CSR and retained project/HiGHS producers.

No native status is a mathematical decision. All vectors remain untrusted.
"""
import math
import os
from pathlib import Path
import re
import subprocess
import time

from lp_baseline_common import (ROOT, checked, equal_f64, load, options, put,
                                require, vector)
from lp_baseline_contract import csr, normalize_original_sense_dual


def result():
    return dict(primal=None, dual=None, reduced_costs=None, native_status='unknown',
                native_solve_ns=None, iterations=None, algorithm_executed=None,
                executed_device='unknown', effective_parameters={}, limitations=[],
                readback=None)


def native_status(name):
    name = str(name).lower().replace('_', '').replace(' ', '')
    if name in ('optimal', 'feasible'): return 'optimal'
    if 'infeasible' in name and 'unbounded' in name: return 'infeasible_or_unbounded'
    if name == 'infeasible': return 'infeasible'
    if name == 'unbounded': return 'unbounded'
    if any(x in name for x in ('limit', 'timeout', 'interrupt')): return 'limit'
    if 'numerical' in name: return 'numerical_failure'
    return 'unknown'


def native_bounds(model, infinity=math.inf):
    arrays = {}
    for side in ('variable', 'row'):
        for suffix, sign in [('lower', -1), ('upper', 1)]:
            key = side + '_' + suffix
            for value in model[key]:
                require(value is None or abs(value) < infinity, 'finite bound exceeds native sentinel')
            arrays[key] = [sign * infinity if x is None else x for x in model[key]]
    return arrays


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
        getattr(dm, 'set_' + key + '_bounds')(np.asarray(values, dtype=np.float64))
    if readback:
        equal_f64(dm.get_constraint_matrix_values(), v)
        require(list(dm.get_constraint_matrix_indices()) == i and list(dm.get_constraint_matrix_offsets()) == p, 'cuOpt CSR readback')
        equal_f64(dm.get_objective_coefficients(), model['objective'])
        equal_f64([dm.get_objective_offset()], [model['offset']])
        require(bool(dm.get_sense()) == (model['sense'] == 'maximize'), 'cuOpt sense readback')
        for key, values in bounds.items(): equal_f64(getattr(dm, 'get_' + key + '_bounds')(), values)
        r['readback'] = 'binary64_and_csr_exact'
    settings = lp.SolverSettings()
    parameters = dict(config['parameters'], time_limit=seconds)
    for key, value in parameters.items():
        settings.set_parameter(key, value)
        observed = settings.get_parameter(key)
        require(observed == value, 'cuOpt parameter readback: ' + key)
        r['effective_parameters'][key] = value
    solution = lp.Solve(dm, settings)
    require(solution is not None, 'cuOpt returned no Solution')
    r.update(primal=vector(solution.get_primal_solution()),
             dual=vector(solution.get_dual_solution()), reduced_costs=vector(solution.get_reduced_cost()),
             native_status=native_status(solution.get_termination_reason()),
             native_solve_ns=round(float(solution.get_solve_time()) * 1e9),
             algorithm_executed=str(solution.get_solved_by()),
             iterations=int(solution.get_lp_stats()['nb_iterations']))
    if r['dual'] is not None:
        r['dual'] = normalize_original_sense_dual(r['dual'], model['sense'])
    r['limitations'].append('GPU execution requires separate affirmative process activity; method selection alone is insufficient.')
    if config['algorithm'] == 'concurrent':
        r['limitations'].append('Concurrent barrier/simplex internal tolerances use native defaults; exported endpoint still requires the strict checker.')
    return r


def copt(model, config, seconds, directory, readback):
    import coptpy as cp
    r = result()
    require(all(x == 0 or abs(x) > 1e-10 for x in model['values'] + model['objective']), 'COPT MatrixTol would filter input')
    bounds = native_bounds(model, cp.COPT.INFINITY)
    env = cp.Envr()
    m = env.createModel('gpup-baseline')
    lines = []
    class Log(cp.LogCallback):
        def Display(self, message): lines.append(message)
    logger = Log()
    m.setLogCallback(logger)
    parameters = dict(config['parameters'], TimeLimit=seconds)
    for key, value in parameters.items():
        m.setParam(key, value)
        observed = m.getParam(key)
        require(observed == value, 'COPT parameter readback: ' + key)
        r['effective_parameters'][key] = observed
    variables = [m.addVar(lb=lo, ub=hi, name='v' + str(id_)) for id_, lo, hi in
                 zip(model['variable_ids'], bounds['variable_lower'], bounds['variable_upper'])]
    p, i, v = csr(model)
    for row, id_ in enumerate(model['row_ids']):
        start, end = p[row:row+2]
        expr = cp.LinExpr([variables[j] for j in i[start:end]], v[start:end])
        m.addBoundConstr(expr, lb=bounds['row_lower'][row], ub=bounds['row_upper'][row], name='r' + str(id_))
    objective = cp.LinExpr(variables, model['objective'])
    objective.addConstant(model['offset'])
    m.setObjective(objective, cp.COPT.MINIMIZE if model['sense'] == 'minimize' else cp.COPT.MAXIMIZE)
    if readback:
        vs, rows = m.getVars(), m.getConstrs()
        for key, field, items in [('objective', 'Obj', vs), ('variable_lower', 'LB', vs),
                ('variable_upper', 'UB', vs), ('row_lower', 'LB', rows), ('row_upper', 'UB', rows)]:
            equal_f64(m.getInfo(field, items), model['objective'] if key == 'objective' else bounds[key])
        equal_f64([m.getAttr('ObjConst')], [model['offset']])
        require(m.getAttr('ObjSense') == (1 if model['sense'] == 'minimize' else -1), 'COPT sense readback')
        matrix = m.getA().tocsc()
        require(matrix.indptr.tolist() == model['column_pointers'] and matrix.indices.tolist() == model['row_indices'], 'COPT CSC readback')
        equal_f64(matrix.data, model['values'])
        r['readback'] = 'binary64_and_csc_exact'
    m.solveLP()
    log = '\n'.join(lines)
    (directory / 'native.log').write_text(log)
    gpu = re.search(r'Starting PDLP solver (?:on|using) GPU 0\b', log) is not None
    status_map = {getattr(cp.COPT, key): name for key, name in [('OPTIMAL','optimal'),
        ('INFEASIBLE','infeasible'), ('UNBOUNDED','unbounded'), ('INF_OR_UNB','infeasible_or_unbounded'),
        ('TIMEOUT','limit'), ('INTERRUPTED','limit'), ('ITERLIMIT','limit')] if hasattr(cp.COPT,key)}
    r.update(native_status=status_map.get(m.getAttr('LpStatus'), 'unknown'),
        iterations=int(m.getAttr('PDLPIter')), native_solve_ns=round(m.getAttr('SolvingTime') * 1e9),
        algorithm_executed='pdlp' if config['algorithm'] == 'pdlp' or m.getAttr('PDLPIter') > 0 else 'native-default-unreported',
        executed_device='gpu' if gpu else ('cpu' if not config['gpu'] else 'unknown'))
    if m.getAttr('HasLpSol'):
        r.update(primal=vector(m.getValues()), dual=normalize_original_sense_dual(list(m.getDuals()), model['sense']))
    r['limitations'].append('COPT exposes no comparable hard PDLP work limit or random seed; precision is opaque.')
    return r


def retained(model, config, seconds, directory, readback, manifest, original):
    r = result()
    solve = options(seconds)
    if config['solver'] == 'highs':
        solve['iteration_limit'] = None
    solve_path = directory / 'solve.json'
    put(solve_path, solve)
    out = directory / 'native.json'
    if config['solver'] == 'highs':
        cmd = [str(checked(manifest['checker'])), 'highs', str(original), str(solve_path), str(out)]
    else:
        retained_config = load(checked(manifest['project_configuration']))
        selector = config['parameters']['execution_config'].split('#')[1]
        c = next(c for c in retained_config['configurations'] if c['id'] == selector)
        method = directory / 'method.json'
        put(method, retained_config['lp_settings'])
        cmd = [str(checked(manifest['project_binary'])), 'lp-study', 'solve', '--model', str(original),
            '--model-byte-limit', str(128 << 20), '--config', str(solve_path), '--backend', c['backend'],
            '--device', manifest['device_uuid'], '--lp-settings', str(method), '--lp-profile', 'false',
            '--lp-device-memory-bytes', str(12 << 30), '--lp-evidence', str(out), '--evidence-format', 'compact-v1']
        for key in ('execution', 'precision'):
            if key in c:
                path = directory / (key + '.json')
                put(path, c[key])
                cmd += ['--lp-' + key, str(path)]
    env = {**os.environ, 'AI_OPTIMIZER_CUDA_DIR': str(ROOT / manifest['project_cuda_directory'])}
    subprocess.run(cmd, check=True, env=env)
    data = load(out)
    if data.get('format') == 'lp-endpoint-compact-v1' or 'endpoint' in data:
        data = data['endpoint']
    record, d = data['record'], data['diagnostics']
    candidate = record['candidate']
    r.update(primal=[a['value'] for a in candidate['values']] if candidate else None,
        dual=d['dual'], iterations=d['iterations'], native_status=native_status(record['termination']),
        algorithm_executed=record['backend'], native_solve_ns=None,
        executed_device='cpu' if config['solver'] == 'highs' else ('gpu' if record['backend'] == 'cuda-lp-tuned' and d['kernel_launches'] > 0 else 'unknown'),
        effective_parameters=solve, readback='retained_original_model_reader' if readback else None)
    r['limitations'].append('Native-only solve duration unavailable in the retained unprofiled interface.')
    return r
