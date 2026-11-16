"""Diagnostic original-row proofs for missing finite variable bounds.

This does not change the solver or reinterpret earlier certificates. Each bound
is entailed by an original row and previously proved bounds using exact rational
arithmetic. The unchanged serial checker assesses the equivalent tightened LP.
Unresolved directions remain infinite. No guessed large bounds are permitted.
"""
import argparse
import copy
from fractions import Fraction as F
import json
import math
import subprocess
import time
from lp_general_common import BASE, ROOT, load, put, ref, require
from lp_general_oracle import BINARY, settings
from lp_general_device import serial


def endpoint(bound):
    return F(bound['value']) if bound['kind'] == 'finite' else None


def outward(value, upper):
    try:
        rounded = float(value)
    except OverflowError:
        return None
    if not math.isfinite(rounded):
        return None
    if (upper and F(rounded) < value) or (not upper and F(rounded) > value):
        rounded = math.nextafter(rounded, math.inf if upper else -math.inf)
    return rounded if math.isfinite(rounded) else None


def derive(model, passes=16):
    result = copy.deepcopy(model)
    variables = {v['id']: v for v in result['variables']}
    proof = []
    for _ in range(passes):
        count = len(proof)
        for row in model['constraints']:
            # Row snapshots: all proposals below depend only on earlier rows.
            products = []
            for term in row['terms']:
                a = F(term['coefficient']); v = variables[term['variable_id']]
                lo, hi = endpoint(v['lower']), endpoint(v['upper'])
                if a < 0:
                    lo, hi = hi, lo
                products.append((F(0),F(0)) if not a else (None if lo is None else a*lo, None if hi is None else a*hi))
            sums = [sum((p[k] for p in products if p[k] is not None), F(0)) for k in (0, 1)]
            missing = [sum(p[k] is None for p in products) for k in (0, 1)]
            proposals = []
            for j, term in enumerate(row['terms']):
                a = F(term['coefficient'])
                if a == 0:
                    continue
                for row_side, k in [('upper', 0), ('lower', 1)]:
                    rhs = endpoint(row[row_side])
                    if rhs is None or missing[k] - (products[j][k] is None):
                        continue
                    side = row_side if a > 0 else ('lower' if row_side == 'upper' else 'upper')
                    v = variables[term['variable_id']]
                    if v[side]['kind'] == 'finite':
                        continue
                    others = sums[k] - (products[j][k] or F(0))
                    value = outward((rhs - others)/a, side == 'upper')
                    if value is not None:
                        proposals.append(dict(row_id=row['id'], variable_id=v['id'], side=side, value=value, row_side=row_side))
            for step in proposals:
                v = variables[step['variable_id']]
                if v[step['side']]['kind'] != 'finite':
                    v[step['side']] = dict(kind='finite', value=step['value']); proof.append(step)
        if len(proof) == count:
            break
    return result, proof


def verify(original, tightened, proof):
    """Independent per-witness exact implication; no aggregate producer sums."""
    expected = copy.deepcopy(original)
    variables = {v['id']: v for v in expected['variables']}
    rows = {r['id']: r for r in original['constraints']}
    for step in proof:
        row = rows[step['row_id']]; target = step['variable_id']; upper = step['row_side'] == 'upper'
        rhs = endpoint(row[step['row_side']]); require(rhs is not None, 'infinite proof row')
        a = None
        for term in row['terms']:
            c = F(term['coefficient'])
            if term['variable_id'] == target:
                a = c
            elif c:
                # Upper row uses a lower bound on all other contributions.
                side = 'lower' if (c > 0) == upper else 'upper'
                b = endpoint(variables[term['variable_id']][side])
                require(b is not None, 'unproved contribution')
                rhs -= c*b
        require(a is not None and a != 0, 'missing target coefficient')
        is_upper = upper == (a > 0)
        require(step['side'] == ('upper' if is_upper else 'lower'), 'proof orientation')
        proposed = F(step['value']); exact = rhs/a
        require(proposed >= exact if is_upper else proposed <= exact, 'inward derived bound')
        require(variables[target][step['side']]['kind'] != 'finite', 'unexpected finite replacement')
        variables[target][step['side']] = dict(kind='finite', value=step['value'])
    require(expected == tightened, 'unproved model change')


def run(identity):
    out = BASE/identity; out.mkdir(parents=True, exist_ok=False); results = []
    for external in load(BASE/'external-reference-v2/result.json')['rows']:
        model_path = ROOT/external['model']['path']; original = load(model_path)
        start = time.monotonic_ns(); tightened, proof = derive(original); elapsed = time.monotonic_ns()-start
        verify(original, tightened, proof)
        i = external['model_index']; path = out/f'm{i:02d}.model.json'; put(path, tightened)
        put(out/f'm{i:02d}.proof.json', dict(original=ref(model_path), tightened=ref(path), steps=proof))
        native = load(ROOT/external['native']['path']); candidate = native['record']['candidate']
        x = [v['value'] for v in candidate['values']]; y = native['diagnostics']['dual']
        requests = [dict(settings={**settings('native'), 'tolerance': t}, primal=x, dual=y) for t in [1e-7, 1e-9]]
        p = subprocess.run([str(BINARY), 'assess', str(path)], input=''.join(json.dumps(q)+'\n' for q in requests), capture_output=True, text=True, check=True)
        (out/f'm{i:02d}.responses.jsonl').write_text(p.stdout)
        certs = [json.loads(s) for s in p.stdout.splitlines()]; require(len(certs) == 2, 'coverage')
        certificates = []
        for j, (q, cert) in enumerate(zip(requests, certs)):
            check = serial(path, dict(primal=x, dual=y, certificate=cert), q['settings']['tolerance'], out, f'm{i:02d}-{j}')
            certificates.append(dict(certificate=cert, serial=check))
        row = dict(model=external['model'], family=external['family'], derived_bounds=len(proof), preparation_ns=elapsed,
                   remaining_infinite=sum(v[s]['kind'] != 'finite' for v in tightened['variables'] for s in ['lower', 'upper']), certificates=certificates)
        results.append(row); print({k:v for k,v in row.items() if k not in ['model','certificates']}, [c['accepted'] for c in certs], flush=True)
    put(out/'result.json', dict(status='complete', rows=results, checker=ref(BINARY),
        scope='exact original-row implications plus unchanged checker; diagnostic only; no solver or historical result changed'))


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--id', required=True); run(p.parse_args().id)
