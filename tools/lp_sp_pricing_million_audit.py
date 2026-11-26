"""CPU-only whole-state differential and rigorous sampled proposal audits."""
import ctypes as C
import json
import time

import numpy as np

from lp_sp_pricing_million import (STUDY, AUX, auxiliary_oracle, validate_freeze,
    PackedBasis, IntervalProof, NativeProof)
from lp_sp_pricing_budget import binding, put
from lp_sp_pricing_gpu_opt_compare import read, verify


def scalar_reference(a, slots, steps, h=4., epsilon=1/65536):
    """Independent NumPy matvec equations; BLAS is restricted to one thread."""
    tau = .9 / np.abs(a).sum(axis=1)
    sums = np.abs(a).sum(axis=0)
    sigma = np.divide(.9, sums, out=np.ones_like(sums), where=sums > 0)
    x = np.zeros((len(slots), a.shape[0])); u = np.zeros((len(slots), a.shape[1]))
    for q, slot in enumerate(slots):
        for _ in range(steps):
            previous = x[q].copy()
            x[q] = np.clip(previous + tau * (a[:, slot] - a @ u[q]), -h, h)
            value = u[q] + sigma * (a.T @ (2*x[q]-previous))
            u[q] = np.maximum(0., value-2*sigma) + np.minimum(0., value+epsilon*sigma)
    return x, u


def difference(a, b):
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise RuntimeError('invalid numerical state')
    return float(np.max(np.abs(a-b)/(1+np.abs(b))))


def main():
    f = validate_freeze()
    if read(STUDY / 'auxiliary-completed.json')['status'] != 'all_cells_attempted':
        raise RuntimeError('auxiliary roster incomplete')
    pairs = []; failures = []; scalar = []; checks = []
    for spec in AUX:
        a, oracle = auxiliary_oracle(spec, seconds=1100)
        packed = PackedBasis(oracle)
        preparation = time.perf_counter_ns()
        with NativeProof(oracle) as exact, IntervalProof(oracle, packed) as interval:
            checker_preparation_ns = time.perf_counter_ns() - preparation
            for cell in [c for c in f['auxiliary_cells'] if c['case']['name'] == spec['name'] and c['lane'] == 'wave']:
                out = STUDY / 'auxiliary' / cell['id']
                left = STUDY / 'auxiliary' / (cell['id'].removesuffix('-wave') + '-lean')
                records = []
                for directory in (left, out):
                    proc = read(directory / 'process.json')
                    if proc['returncode'] != 0 or proc['timed_out'] or not (directory / 'response.json').exists():
                        failures.append(dict(cell=directory.name, process=proc)); records.append(None)
                    else:
                        response = read(directory / 'response.json')
                        verify(response['x']); verify(response['u'])
                        records.append(dict(response=response, process=proc,
                            x=np.load(response['x']['path'], allow_pickle=False),
                            u=np.load(response['u']['path'], allow_pickle=False)))
                if any(r is None for r in records):
                    continue
                control, wave = records
                maximum = max(difference(wave['x'], control['x']), difference(wave['u'], control['u']))
                if maximum > 1e-12:
                    raise RuntimeError('full lean/wave state disagreement')
                pairs.append(dict(case=spec['name'], storage=cell['storage'], width=cell['width'],
                    repetition=cell['repetition'], normalized_difference=maximum,
                    lean=control['response'], wave=wave['response'],
                    lean_process_ns=control['process']['elapsed_ns'], wave_process_ns=wave['process']['elapsed_ns']))
                if cell['width'] == 64 and cell['repetition'] == 0:
                    expected_x, expected_u = scalar_reference(a, [0, 63], f['auxiliary_steps'])
                    error = max(difference(wave['x'][[0, 63]], expected_x), difference(wave['u'][[0, 63]], expected_u))
                    if error > 1e-10:
                        raise RuntimeError('independent CPU equations disagree')
                    scalar.append(dict(case=spec['name'], storage=cell['storage'], proposals=2, normalized_difference=error))
                ids = [0, cell['width']//3, 2*cell['width']//3, cell['width']-1]
                x = np.ascontiguousarray(wave['x'][ids]); u = np.ascontiguousarray(wave['u'][ids])
                costs = {}; decisions = {}; stats = None
                for lane in (('gmp', 'interval') if cell['repetition'] % 2 == 0 else ('interval', 'gmp')):
                    begin = time.perf_counter_ns(); known = {}
                    if lane == 'interval':
                        known, stats = interval.batch(ids, [1]*len(ids),
                            x.ctypes.data_as(C.POINTER(C.c_double)), u.ctypes.data_as(C.POINTER(C.c_double)), {})
                    else:
                        for q, slot in enumerate(ids):
                            if slot//2 in known: continue
                            found = exact.labels(slot//2, x[q].tolist(), u[q].tolist())
                            known.update(found['established'])
                    costs[lane] = time.perf_counter_ns()-begin; decisions[lane] = known
                if any(decisions['gmp'].get(i) != sign for i, sign in decisions['interval'].items()):
                    raise RuntimeError('rigorous interval label not established by GMP')
                checks.append(dict(cell=cell['id'], case=spec['name'], sampled_slots=ids,
                    gmp_ns=costs['gmp'], interval_ns=costs['interval'], interval=stats,
                    gmp_labels=len(decisions['gmp']), interval_labels=len(decisions['interval']),
                    coverage_equal=decisions['gmp'] == decisions['interval'],
                    shared_checker_preparation_ns=checker_preparation_ns,
                    response=binding(out / 'response.json')))
                print(json.dumps(dict(cell=cell['id'], normalized_difference=maximum,
                    gmp_ms=costs['gmp']/1e6, interval_ms=costs['interval']/1e6)), flush=True)
    put(STUDY / 'auxiliary-audit.json', dict(status='audited', pairs=pairs, failures=failures,
        scalar=scalar, checks=checks, tested_pair_count=len(pairs),
        rigor='interval decisions verified against GMP; whole numerical states are differential tests, not LP certificates'))


if __name__ == '__main__': main()
