"""Additional large-model corruption checks, separate from solver timings."""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
import scipy.sparse as sparse
from lp_sp_pricing_budget import ROOT, BASE, put, binding
from lp_sp_pricing_gpu_opt_compare import read, verify
from lp_sp_pricing_scale_experiment import STUDY, validate
from lp_sp_pricing_scale_verify import vector, verify_arrays
from lp_billion_arrays import read as read_array

sys.path.insert(0, str(ROOT/'research/lp-sp-pricing/python'))
from sp_pricing.certificate_guard import guarded_certificate

PLAN = BASE/'scale-challenge-plan-v1.json'
RESULT = BASE/'scale-challenge-v1/result.json'


def freeze():
    validate()
    put(PLAN, dict(status='frozen', source=binding(__file__),
        experiment=binding(STUDY/'freeze.json'),
        selection='every independently accepted candidate in both new groups',
        mutations=['objective[0] += 2**-16 with unchanged endpoint',
                   'dual[0] = -1 with unchanged model and primal'],
        required='native guarded checker and arbitrary-precision oracle reject both mutations',
        immutable_inputs=True, solver_reexecution=False,
        timing='additional research assurance; excluded from all solver complete times'))


def dyadic(values):
    integers, denominator = vector(values)
    if denominator & (denominator-1):
        raise ValueError('native challenge requires dyadic certificate')
    exponent = denominator.bit_length()-1
    if exponent > 24 or any(abs(v) > 1 << 40 for v in integers):
        raise ValueError('native challenge exceeds admitted bounds')
    return np.asarray(integers, dtype=np.int64), exponent


def run():
    start = time.perf_counter_ns()
    frozen = validate()
    plan = read(PLAN)
    verify(plan['source']); verify(plan['experiment'])
    rows = [r for group in (0, 1) for r in read(STUDY/f'audits-group-{group}.json')['rows']]
    selected = [r for r in rows if r['lane'] == 'candidate' and r['independent_exact_accepted']]
    out = RESULT.parent
    out.mkdir(exist_ok=False)
    checks = []
    for row in selected:
        model = frozen['models'][row['model_index']]
        raw = read(model['model']['path'])
        values = {k: read_array(BASE, v) for k, v in raw['arrays'].items()}
        a = sparse.csr_matrix((values['values'], values['indices'], values['offsets']),
                              shape=(raw['rows'], raw['columns']))
        b = values['row_upper']
        c = np.zeros(raw['columns'])
        c[values['objective_indices']] = values['objective_values']
        verify(row['response']); verify(row['independent_proof'])
        cert = read(row['response']['path'])['certificate']
        x, px = dyadic(cert['x']); y, py = dyadic(cert['y'])
        if not guarded_certificate(a, b, c, x, px, y, py):
            raise ArithmeticError('original admitted certificate unexpectedly rejected')
        changed = c.copy(); changed[0] += 2.0**-16
        bad_y = y.copy(); bad_y[0] = -(1 << py)
        mutations = [('objective', changed, y, cert['y']),
                     ('dual_sign', c, bad_y, [-1]+cert['y'][1:])]
        for name, objective, native_y, exact_y in mutations:
            native = guarded_certificate(a, b, objective, x, px, native_y, py)
            independent = verify_arrays(values['offsets'], values['indices'], values['values'],
                                        b, objective, cert['x'], exact_y, seconds=210)
            if native or independent['accepted']:
                raise ArithmeticError('deliberately invalid certificate accepted')
            if name == 'objective' and (independent.get('dual_equations') is not False
                    or independent.get('visited_nonzeros') != raw['nonzeros']):
                raise ArithmeticError('objective corruption did not receive complete independent check')
            checks.append(dict(id=row['id'], mutation=name, native_accepted=native,
                               independent=independent, response=row['response']))
        print(json.dumps(dict(id=row['id'], corruption_checks=2, nonzeros=raw['nonzeros'])), flush=True)
    put(RESULT, dict(status='passed', plan=binding(PLAN), source=binding(__file__),
        accepted_candidates=len(selected), mutation_checks=len(checks), checks=checks,
        elapsed_ns=time.perf_counter_ns()-start,
        scope='all new accepted candidates; no solver reruns; immutable original inputs'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['freeze', 'run'])
    args = p.parse_args()
    freeze() if args.action == 'freeze' else run()
