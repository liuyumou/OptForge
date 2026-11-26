"""Immutable million-scale diagnostics; no change to admitted numerical sources."""
import argparse
import ctypes as C
from fractions import Fraction as Q
import json
from pathlib import Path
import sys
import time
import subprocess
from types import SimpleNamespace

import numpy as np
from scipy import sparse

from lp_sp_pricing_budget import BASE, ROOT, CPU, GPU, NS, accounting, binding, put
from lp_sp_pricing_gpu_opt_compare import read, verify
from lp_sp_pricing_wave_measure import admission
from lp_sp_pricing_wave_quality import validate, sources as wave_sources
from lp_sp_pricing_wave_policy import validate_policy
from lp_sp_pricing_baselines import PYTHON, images, audit, launch
from lp_billion_arrays import write
from lp_billion_owned_process import execute
from sp_pricing.exact import Work, Limit
from sp_pricing.solver import PricingSolver
from sp_pricing.gpu_wave import WaveEngine, PackedBasis, IntervalProof
from sp_pricing.gpu_lean import LeanBatch
from sp_pricing.native_proof import NativeProof


STUDY = BASE / 'million-v1'
LEAN = ROOT / 'research/lp-sp-pricing/target/release/libsp_batch_optimized.so'
AUX = [dict(name='dense-square', r=1000, s=1000, degree=1000),
       dict(name='dense-wide', r=500, s=2000, degree=2000),
       dict(name='sparse-wide', r=500, s=2000, degree=32)]
ORIGINAL = [dict(name='dense', m=1000, n=1000, degree=1000, shift=1),
            dict(name='tall', m=4000, n=1000, degree=250, shift=1),
            dict(name='sparse', m=8000, n=8000, degree=125, shift=1)]


def matrix(m, n, degree, seed, shift=17):
    """Canonical positive dyadic CSR, with exactly m*degree nonzeros."""
    if min(m, n, degree) < 1 or degree > n:
        raise ValueError('matrix shape')
    indices = np.sort((np.arange(m)[:, None] * shift + np.arange(degree)[None, :]) % n, axis=1)
    rng = np.random.default_rng(seed)
    values = rng.integers(1, 32, size=m * degree, dtype=np.int32).astype(np.float64) / 16
    offsets = np.arange(m + 1, dtype=np.int64) * degree
    return sparse.csr_matrix((values, indices.ravel(), offsets), shape=(m, n))


def capacity(m, n):
    geometry, paired = (m + 1) * (n + 1), 2 * (m + 1) ** 2
    reason = ('explicit_reference_geometry_limit' if geometry > 100000 else
              'paired_basis_fill_limit' if paired > 1000000 else None)
    return dict(status='unsupported_capacity' if reason else 'within_initial_geometry_limits',
                reason=reason, geometry_entries=geometry, paired_entries=paired,
                geometry_cap=100000, paired_cap=1000000,
                basis_and_transpose_fp64_bytes=16 * paired)


def original_model(spec, directory):
    start = time.perf_counter_ns()
    a = matrix(spec['m'], spec['n'], spec['degree'], 121951, spec['shift'])
    m, n = a.shape
    x = np.ones(n)
    denominator = 1 << (m - 1).bit_length()
    y = np.full(m, 1 / denominator)
    b = a @ x
    c = np.asarray(a.T @ y).ravel()
    arrays = dict(column_ids=write(BASE, np.arange(n), 'u32le'),
        row_ids=write(BASE, np.arange(m), 'u32le'),
        column_lower=write(BASE, np.full(n, -np.inf)), column_upper=write(BASE, np.full(n, np.inf)),
        row_lower=write(BASE, np.full(m, -np.inf)), row_upper=write(BASE, b),
        offsets=write(BASE, a.indptr, 'u64le'), indices=write(BASE, a.indices, 'u32le'),
        values=write(BASE, a.data), objective_indices=write(BASE, np.arange(n), 'u32le'),
        objective_values=write(BASE, c))
    path = directory / 'portable.json'
    put(path, dict(schema_version=1, model_id=spec['name']+'-million-121951', rows=m,
        columns=n, nonzeros=int(a.nnz), sense='maximize', offset=0., arrays=arrays))
    encoding_ns = time.perf_counter_ns() - start
    witness = directory / 'construction'
    witness.mkdir()
    put(witness / 'response.json', dict(endpoint=dict(primal=write(BASE, x), dual=write(BASE, -y))))
    proof = audit('copt_scale_off', path, path, witness)
    if not proof['accepted']:
        raise RuntimeError('planted original-model certificate failed strict independent audit')
    return dict(**spec, nonzeros=int(a.nnz), model=binding(path), encoding_ns=encoding_ns,
                construction_audit=binding(witness / 'audit.json'), capacity=capacity(m, n))


def freeze():
    gate = admission()
    validate_policy()
    subprocess.run([str(PYTHON), '-B', '-m', 'unittest', 'discover', '-s', 'tests/integration',
                    '-p', 'test_lp_sp_pricing_million.py', '-v'], cwd=ROOT, check=True)
    # The current preparation reservation belongs to development. Check the
    # untouched future GPU phase here; the wrapper enforces all CPU phase caps.
    confirmation_gpu = 0
    for p in (BASE / 'resources').glob('*.reservation.json'):
        if read(p)['phase'] == 'confirmation':
            confirmation_gpu += read(p.with_name(p.name.replace('.reservation.', '.settlement.')))['gpu_ns']
    if confirmation_gpu + 360 * NS > GPU['confirmation'] * NS:
        raise RuntimeError('original-LP reservation does not fit remaining confirmation allocation')
    STUDY.mkdir(exist_ok=False)
    models = []
    for spec in ORIGINAL:
        directory = STUDY / 'models' / spec['name']
        directory.mkdir(parents=True)
        models.append(original_model(spec, directory))
    cells = []
    for case in AUX:
        for storage in ('dense', 'csr'):
            for width in (64, 256, 1000):
                for rep in range(3):
                    for lane in (('lean', 'wave') if rep % 2 == 0 else ('wave', 'lean')):
                        cells.append(dict(id=f"{case['name']}-{storage}-{width}-r{rep}-{lane}",
                            case=case, storage=storage, width=width, repetition=rep, lane=lane))
    paths = list((ROOT / 'research/lp-sp-pricing/python').rglob('*.py'))
    paths += list((ROOT / 'research/lp-sp-pricing/native').glob('*.*'))
    paths += list((ROOT / 'tools').glob('lp_sp_pricing_million*.py'))
    paths += list((ROOT / 'tests/integration').glob('test_lp_sp_pricing_million*.py'))
    paths += [ROOT / 'tools' / n for n in ['lp_sp_pricing_baselines.py', 'lp_sp_pricing_guard.py',
        'lp_sp_pricing_budget.py', 'lp_sp_pricing_wave_run.py', 'lp_sp_pricing_wave_policy_run.py']]
    put(STUDY / 'freeze.json', dict(status='frozen', generator_contract_tests=5, gate=gate, wave_sources=wave_sources(),
        sources=[binding(p) for p in sorted(set(paths))], lean=binding(LEAN), images=images(),
        auxiliary_cells=cells, auxiliary_steps=128, auxiliary_process_seconds=10,
        auxiliary_outer_seconds=1300, auxiliary_audit_seconds=1200,
        original_models=models, original_repetitions=2, original_native_seconds=30,
        original_process_seconds=45, original_outer_seconds=360,
        scope='million-nonzero original LPs plus separate million-entry auxiliary throughput',
        limitations=['original candidate is capacity-refused before numerical execution',
            'dense auxiliary cases have one million nonzeros; sparse auxiliary has 16000 nonzeros in one million positions',
            'auxiliary matrices are synthetic bounded LPs, not derived original-LP calibrations',
            'whole numerical states are compared; exact checks sample four proposals per wave cell',
            'cold auxiliary process time is not complete original-LP solve time',
            'three auxiliary and two original-LP repetitions; unflushed caches']))
    print(json.dumps(dict(status='frozen', auxiliary_cells=len(cells), original_models=len(models))), flush=True)


def validate_freeze():
    f = read(STUDY / 'freeze.json')
    verify(f['gate']); validate(f['gate']['path']); verify(f['lean'])
    for item in f['sources'] + f['wave_sources']:
        verify(item)
    for model in f['original_models']:
        verify(model['model']); verify(model['construction_audit'])
    if images() != f['images']:
        raise RuntimeError('baseline image changed')
    return f


def auxiliary_oracle(spec, seconds=300):
    a = matrix(spec['r'], spec['s'], spec['degree'], 121953).toarray()
    pool = {i: Q(i, 16) for i in range(32)}
    b = [[pool[int(v * 16)] for v in row] for row in a]
    # These diagnostics test the bounded auxiliary equations only. No paired
    # space theorem or opposite-slot broadcast is assumed for arbitrary matrices.
    o = SimpleNamespace(b=b, r=spec['r'], n=spec['s']//2, h=Q(4), epsilon=Q(1, 65536),
                        broadcast_negative=False, epoch=0,
                        work=Work(seconds=seconds, max_operations=4000000000))
    return a, o


def child(cell_id):
    f = validate_freeze()
    cell = next(c for c in f['auxiliary_cells'] if c['id'] == cell_id)
    out = STUDY / 'auxiliary' / cell_id
    start = time.perf_counter_ns()
    _, oracle = auxiliary_oracle(cell['case'])
    generated = time.perf_counter_ns()
    width, steps = cell['width'], f['auxiliary_steps']
    slots = list(range(width))
    x = np.empty((width, oracle.r)); u = np.empty((width, 2 * oracle.n))
    sparse_mode = cell['storage'] == 'csr'
    device = 0.; dispatch_ns = 0; state_ns = 0; init_ns = None; components = None
    if cell['lane'] == 'wave':
        packed = PackedBasis(oracle)
        with WaveEngine() as engine:
            init_ns = engine.initialization_ns
            components = engine.load(oracle, slots, packed, sparse_mode)
            prepared = time.perf_counter_ns()
            result = engine.advance(steps, [1] * width)
            device = result['device_iteration_ms']; dispatch_ns = result['elapsed_ns']
            copied = time.perf_counter_ns()
            x[:] = np.ctypeslib.as_array(engine.x, shape=(width * oracle.r,)).reshape(x.shape)
            u[:] = np.ctypeslib.as_array(engine.u, shape=(width * 2 * oracle.n,)).reshape(u.shape)
            state_ns = time.perf_counter_ns() - copied
    else:
        with LeanBatch(LEAN, oracle.b, sparse_mode) as engine:
            prepared = time.perf_counter_ns()
            for first in range(0, width, 64):
                requested = slots[first:first+64]
                padded = requested + [requested[-1]] * (64-len(requested))
                tick = time.perf_counter_ns()
                engine.begin(padded, oracle.h, oracle.epsilon)
                engine.active([int(i < len(requested)) for i in range(64)])
                result = engine.advance(steps)
                dispatch_ns += time.perf_counter_ns() - tick
                device += result['device_iteration_ms']
                copied = time.perf_counter_ns()
                x[first:first+len(requested)] = np.ctypeslib.as_array(engine.x).reshape(64, oracle.r)[:len(requested)]
                u[first:first+len(requested)] = np.ctypeslib.as_array(engine.u).reshape(64, 2*oracle.n)[:len(requested)]
                state_ns += time.perf_counter_ns() - copied
    numerical_ns = time.perf_counter_ns() - start
    if not np.isfinite(x).all() or not np.isfinite(u).all():
        raise RuntimeError('nonfinite auxiliary state')
    np.save(out / 'x.npy', x, allow_pickle=False); np.save(out / 'u.npy', u, allow_pickle=False)
    put(out / 'response.json', dict(status='completed', cell=cell, steps=steps,
        generation_ns=generated-start, preparation_ns=prepared-generated,
        initialization_ns=init_ns, preparation_components=components,
        dispatch_ns=dispatch_ns, state_copy_ns=state_ns, device_ms=device, numerical_ns=numerical_ns,
        x=binding(out / 'x.npy'), u=binding(out / 'u.npy'), labels_accepted=False))


def auxiliary_worker():
    f = validate_freeze()
    for cell in f['auxiliary_cells']:
        out = STUDY / 'auxiliary' / cell['id']; out.mkdir(parents=True, exist_ok=False)
        command = [str(PYTHON), '-B', __file__, 'child', '--cell', cell['id']]
        put(out / 'started.json', dict(cell=cell, command=command))
        proc = execute(command, out / 'stdout', out / 'stderr', f['auxiliary_process_seconds'], None)
        put(out / 'process.json', proc)
        print(json.dumps(dict(cell=cell['id'], process=proc)), flush=True)
    put(STUDY / 'auxiliary-completed.json', dict(status='all_cells_attempted'))


def original_worker():
    f = validate_freeze()
    # Check the real candidate's guards using metadata only, without constructing
    # an invalid dense Python input or calling a numerical solver.
    class SizedOnly:
        def __init__(self, n): self.n = n
        def __len__(self): return self.n
        def __iter__(self): raise AssertionError('capacity preflight accessed coefficients')
    refusals = []
    for model in f['original_models']:
        for lane in ('cpu', 'opportunistic'):
            try:
                PricingSolver().feasibility(SizedOnly(model['m']), SizedOnly(model['m']), model['n'])
            except Limit as error:
                if str(error) != model['capacity']['reason']: raise
            else: raise RuntimeError('expected original candidate capacity refusal')
            refusals.append(dict(model=model['name'], lane=lane, attempted=False,
                status='unsupported_capacity', reason=model['capacity']['reason'], certificate=False))
    put(STUDY / 'capacity.json', dict(rows=refusals, source=binding(ROOT / 'research/lp-sp-pricing/python/sp_pricing/solver.py')))
    cells = []
    for rep in range(f['original_repetitions']):
        models = f['original_models']
        for model in models[rep:] + models[:rep]:
            name = model['name'] + f'-r{rep}-copt'
            out = STUDY / 'original' / name; out.parent.mkdir(exist_ok=True)
            proc = launch('copt_scale_off', Path(model['model']['path']), Path(model['model']['path']),
                          out, f['original_native_seconds'], f['original_process_seconds'])
            cells.append(dict(id=name, model=model['name'], repetition=rep, process=proc))
            print(json.dumps(cells[-1]), flush=True)
    put(STUDY / 'original-completed.json', dict(status='all_cells_attempted', cells=cells))


def original_audit():
    f = validate_freeze(); done = read(STUDY / 'original-completed.json'); rows = []
    for cell in done['cells']:
        model = next(m for m in f['original_models'] if m['name'] == cell['model'])
        out = STUDY / 'original' / cell['id']; proc = cell['process']
        response = read(out / 'response.json') if (out / 'response.json').exists() else {}
        proof = audit('copt_scale_off', Path(model['model']['path']), Path(model['model']['path']), out)
        timely = (proc['returncode'] == 0 and not proc['timed_out'] and
                  response.get('native_ns', float('inf')) <= f['original_native_seconds'] * NS)
        rows.append(dict(**cell, status=response.get('status', 'missing_response'), timely=timely,
            accepted=proof['accepted'], gpu_confirmed=response.get('gpu_confirmed', False),
            native_ns=response.get('native_ns'), encoding_ns=model['encoding_ns'], audit_ns=proof['elapsed_ns'],
            complete_ns=model['encoding_ns'] + proc['elapsed_ns'] + proof['elapsed_ns'],
            response=binding(out / 'response.json') if response else None, audit=binding(out / 'audit.json')))
    put(STUDY / 'original-results.json', dict(status='audited', rows=rows, capacity=binding(STUDY / 'capacity.json')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['freeze', 'child', 'auxiliary', 'original', 'audit-original'])
    parser.add_argument('--cell')
    args = parser.parse_args()
    if args.action == 'freeze': freeze()
    elif args.action == 'child': child(args.cell)
    elif args.action == 'auxiliary': auxiliary_worker()
    elif args.action == 'original': original_worker()
    else: original_audit()
