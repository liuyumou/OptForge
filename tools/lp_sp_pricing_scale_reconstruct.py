"""Common endpoint reconstruction, with no factorization or LP reexecution.

This post-hoc tier applies the candidate's fixed dyadic ladder to every available
endpoint, including vendor outputs. Raw outcomes and their timings are immutable.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import sys
import time
import numpy as np
import scipy.sparse as sparse
from lp_sp_pricing_budget import ROOT, BASE, NS, put, binding
from lp_sp_pricing_scale_experiment import STUDY as PRIMARY, validate as primary
from lp_sp_pricing_scale_long import STUDY as LONG, validate as longer
from lp_sp_pricing_scale_seal import RESULT as SEAL, checked as checked_seal
from lp_sp_pricing_gpu_opt_compare import read, verify
from lp_sp_pricing_baselines import PYTHON, audit
from lp_sp_pricing_scale_verify import verify_arrays
from lp_billion_arrays import read as read_array, write as write_array
from lp_billion_owned_process import execute

sys.path.insert(0, str(ROOT/'research/lp-sp-pricing/python'))
from sp_pricing.geometry_fast import dyadic_integers
from sp_pricing.certificate_guard import guarded_certificate

STUDY = BASE/'scale-reconstruction-v1'


def reconstruct(a, b, c, x, y, seconds=60):
    start = time.perf_counter_ns(); deadline = time.monotonic()+seconds
    encoded = dyadic_integers([a.data, b, c])
    if encoded is None or not np.isfinite(x).all() or not np.isfinite(y).all():
        return None, dict(accepted=False, reason='unsupported_input')
    choices = []
    for vector, primal in ((x, True), (y, False)):
        candidates, seen = [], set()
        for exponent in range(25):
            if time.monotonic() > deadline:
                return None, dict(accepted=False, reason='reconstruction_deadline')
            rounded = np.rint(np.ldexp(vector, exponent))
            if (np.abs(rounded) > 2**40).any():
                break
            integer = np.ascontiguousarray(rounded, dtype=np.int64)
            point = np.ldexp(integer.astype(float), -exponent)
            key = point.tobytes()
            if key in seen:
                continue
            seen.add(key)
            if primal:
                if np.max(a@point-b, initial=0) > 1e-9*(1+np.max(np.abs(b), initial=0)):
                    continue
            elif (point < 0).any() or np.max(np.abs(a.T@point-c), initial=0) > 1e-9*(1+np.max(np.abs(c), initial=0)):
                continue
            candidates.append((integer, exponent))
        choices.append(candidates)
    checks = 0
    for xv, px in choices[0]:
        for yv, py in choices[1]:
            if time.monotonic() > deadline:
                return None, dict(accepted=False, reason='reconstruction_deadline', checks=checks)
            checks += 1
            if guarded_certificate(a, b, c, xv, px, yv, py, encoded):
                def rational(v, exponent):
                    q = Fraction(int(v), 1 << exponent)
                    return dict(numerator=str(q.numerator), denominator=str(q.denominator))
                certificate = dict(status='optimal', x=[rational(v, px) for v in xv], y=[rational(v, py) for v in yv])
                return (certificate, np.ldexp(xv.astype(float), -px), np.ldexp(yv.astype(float), -py)), dict(
                    accepted=True, checks=checks, primal_exponent=px, dual_exponent=py, elapsed_ns=time.perf_counter_ns()-start)
    return None, dict(accepted=False, reason='no_exact_dyadic_reconstruction', checks=checks,
                      elapsed_ns=time.perf_counter_ns()-start)


def admit():
    primary(); longer(); checked_seal(); STUDY.mkdir(exist_ok=False)
    # Check reconstruction from perturbed endpoints without using the witness
    # in the reconstruction function. Invalid sign/objective cases cannot pass.
    passed = 0
    for seed in range(32):
        rng = np.random.default_rng(123001+seed); n = 3+seed % 7
        a = sparse.diags(rng.integers(1, 8, size=n)/16, format='csr')
        x = rng.integers(-8, 9, size=n)/8; y = rng.integers(1, 8, size=n)/128
        b = a@x; c = np.asarray(a.T@y)
        endpoint, metadata = reconstruct(a, b, c, x+1e-12, y-1e-12)
        if not metadata['accepted'] or not verify_arrays(a.indptr, a.indices, a.data, b, c, endpoint[0]['x'], endpoint[0]['y'])['accepted']:
            raise ArithmeticError('valid reconstruction test failed')
        if reconstruct(a, b, c, x, -y)[1]['accepted']:
            raise ArithmeticError('negative dual reconstruction accepted')
        passed += 2
    put(STUDY/'plan.json', dict(status='admitted_frozen', tests=passed, source=binding(__file__),
        primary=binding(PRIMARY/'freeze.json'), supplement=binding(LONG/'freeze.json'),
        failed_group_disposition=binding(SEAL),
        selection='all 39 roster slots; every available endpoint receives the same reconstruction; missing endpoints remain unsuccessful',
        policy='unchanged candidate exponent ladder 0..24, bound 2**40, rejection-only 1e-9 residual screens, guarded exact original-model acceptance',
        factorization=False, lp_reexecution=False, process_seconds=90, work_seconds=60,
        disclosure='Post-hoc certificate-format diagnostic after first-seed raw audits; raw COPT and candidate outputs remain unchanged. Charge the same reconstruction and cold independent audits to each available endpoint.'))
    print(json.dumps(dict(status='admitted_frozen', checks=passed)), flush=True)


def validate():
    primary(); longer(); p = read(STUDY/'plan.json')
    for key in ('source', 'primary', 'supplement', 'failed_group_disposition'):
        verify(p[key])
    if read(BASE/'resources/scale-reconstruction-admit-v1.settlement.json')['status'] != 'passed':
        raise RuntimeError('reconstruction admission supervision failed')
    return p


def child(model, response, out):
    plan = validate(); start = time.perf_counter_ns()
    raw = read(model); original = read(response)
    arrays = {k:read_array(BASE, v) for k, v in raw['arrays'].items()}
    a = sparse.csr_matrix((arrays['values'], arrays['indices'], arrays['offsets']), shape=(raw['rows'], raw['columns']))
    c = np.zeros(raw['columns']); c[arrays['objective_indices']] = arrays['objective_values']
    x = read_array(BASE, original['endpoint']['primal']); y = -read_array(BASE, original['endpoint']['dual'])
    endpoint, metadata = reconstruct(a, arrays['row_upper'], c, x, y, plan['work_seconds'])
    result = dict(status='reconstructed' if endpoint else 'not_reconstructed', reconstruction=metadata,
                  original_response=binding(response), model=binding(model))
    if endpoint:
        certificate, px, py = endpoint
        result.update(certificate=certificate, endpoint=dict(primal=write_array(BASE, px), dual=write_array(BASE, -py)))
    result['elapsed_ns'] = time.perf_counter_ns()-start
    put(out/'response.json', result)


def run():
    plan = validate(); main = primary(); extra = longer()
    excluded = set(checked_seal()['timing_excluded_ids'])
    rows = [r for g in (0, 1) for r in read(PRIMARY/f'audits-group-{g}.json')['rows']]+read(LONG/'audits.json')['rows']
    if len(rows) != 39:
        raise RuntimeError('incomplete original roster')
    results = []
    for original in rows:
        model = (extra if original['group'] == 2 else main)['models'][original['model_index']]
        row = dict(id=original['id'], family=original['family'], seed=original['seed'], lane=original['lane'],
                   timely=original['timely'] and original['id'] not in excluded,
                   timing_eligible=original['id'] not in excluded, observed_native_timely=original['timely'],
                   raw_strict_accepted=original['strict_accepted'],
                   accepted=False, native_allowance_seconds=300 if original['group'] == 2 else 120)
        response = read(original['response']['path']) if original.get('response') else {}
        if not response.get('endpoint'):
            row['reason'] = 'no_returned_endpoint'; results.append(row); continue
        out = STUDY/'runs'/original['id']; out.mkdir(parents=True, exist_ok=False)
        cmd = [str(PYTHON), '-B', __file__, 'child', '--model', model['model']['path'],
               '--response', original['response']['path'], '--output', str(out)]
        proc = execute(cmd, out/'stdout', out/'stderr', plan['process_seconds'], None)
        put(out/'process.json', proc)
        reconstructed = read(out/'response.json') if (out/'response.json').exists() else {}
        strict = audit('copt_scale_off', Path(model['model']['path']), Path(model['model']['path']), out)
        independent_start = time.perf_counter_ns(); proof = dict(accepted=False, reason='not_reconstructed')
        if reconstructed.get('endpoint'):
            cmd = [str(PYTHON), '-B', str(ROOT/'tools/lp_sp_pricing_scale_verify.py'), model['model']['path'],
                   str(out/'response.json'), str(out/'independent-exact.json'), '--seconds', '210']
            audit_proc = execute(cmd, out/'independent-stdout', out/'independent-stderr', 240, None)
            put(out/'independent-process.json', audit_proc)
            if audit_proc['returncode'] == 0 and not audit_proc['timed_out'] and (out/'independent-exact.json').exists():
                proof = read(out/'independent-exact.json')
            if not proof['accepted'] or not strict['accepted']:
                raise ArithmeticError('reconstructed exact endpoint failed an independent audit')
        independent_ns = time.perf_counter_ns()-independent_start
        accepted = bool(proc['returncode'] == 0 and not proc['timed_out'] and strict['accepted'] and proof['accepted'])
        # Alternative complete pipeline replaces the raw endpoint audit with
        # reconstruction + audits. The original solve/startup/encoding is kept.
        row.update(accepted=accepted, reason=reconstructed.get('reconstruction', {}).get('reason'),
            process_ns=proc['elapsed_ns'], strict_audit_ns=strict['elapsed_ns'], independent_audit_ns=independent_ns,
            operational_complete_ns=original['encoding_ns']+original['process_ns']+proc['elapsed_ns']+strict['elapsed_ns'],
            complete_ns=original['encoding_ns']+original['process_ns']+proc['elapsed_ns']+strict['elapsed_ns']+independent_ns,
            reconstruction=reconstructed.get('reconstruction'), original_response=original['response'],
            response=binding(out/'response.json') if reconstructed else None, strict_audit=binding(out/'audit.json'),
            independent_proof=binding(out/'independent-exact.json') if (out/'independent-exact.json').exists() else None,
            process=binding(out/'process.json'))
        results.append(row)
        print(json.dumps({k:row[k] for k in ['id', 'accepted', 'reason', 'complete_ns']}), flush=True)
    pairs = []
    for model in main['models']+extra['models']:
        group = {r['lane']:r for r in results if r['family'] == model['name'] and r['seed'] == model['seed']}
        for lane in ('copt-gpu', 'copt-auto'):
            a, b = group['candidate'], group[lane]
            jointly = all(r['timely'] and r['accepted'] for r in (a, b))
            pairs.append(dict(family=model['name'], seed=model['seed'], vendor=lane, jointly_timely_exact=jointly,
                operational_copt_over_candidate=b['operational_complete_ns']/a['operational_complete_ns'] if jointly else None,
                fully_audited_copt_over_candidate=b['complete_ns']/a['complete_ns'] if jointly else None))
    put(STUDY/'result.json', dict(status='all_endpoints_disposed', plan=binding(STUDY/'plan.json'), rows=results,
        pairs=pairs, interpretation='separate common-reconstruction pipeline, not raw vendor certification or a repeated solver run'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['admit', 'run', 'child'])
    p.add_argument('--model', type=Path); p.add_argument('--response', type=Path); p.add_argument('--output', type=Path)
    args = p.parse_args()
    if args.action == 'admit': admit()
    elif args.action == 'run': run()
    else: child(args.model, args.response, args.output)
