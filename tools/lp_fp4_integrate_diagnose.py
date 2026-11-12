"""CPU-only diagnosis of retained SPEC-0030 records; never launches a solver.

The optional microprofile repeats model construction and evidence serialization,
not trajectories or certification. Its timings are separate from the frozen study.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import time

import numpy as np

from lp_baseline_common import ROOT, checked, load, put, ref
from lp_fp4_fast_prepare import encode_batch, FP4_VALUES
from lp_fp4_integrate_model import model

BASE = ROOT / 'artifacts/gpup-fp4-integrate-diagnosis-v1'
STUDY = ROOT / 'artifacts/gpup-fp4-integrate-v1/performance-v1/result.json'
TERMS = ('operator', 'instruction', 'combine', 'scalar', 'projection', 'encoding', 'discarded')


def representation_error(raw, components):
    """Exact-residual CPU re-encoding of an existing endpoint, not a new solve."""
    blocks = np.asarray(raw).reshape(-1, 32)
    words, exponents = encode_batch(blocks, 4, components, arrays=True)
    words = words.reshape(len(blocks), components, 4)
    codes = ((words[..., None] >> np.arange(0, 32, 4)) & 15).reshape(len(blocks), components, 32)
    values = FP4_VALUES[codes & 7] * np.where(codes & 8, -1., 1.)
    decoded = np.ldexp(values, exponents.reshape(len(blocks), components, 1)).sum(axis=1)
    error = np.abs(blocks - decoded).reshape(5, -1)
    return dict(zip(('x', 'y', 'bar', 'anchor_x', 'anchor_y'), error.max(axis=1).tolist()))


def diagnosis(output):
    study = load(STUDY)
    rows = study['rows']
    details = {r['id']: load(checked(r['result'])) for r in rows}
    for row in rows:
        detail = details[row['id']]
        assert sum(row['costs_ns'].values()) == row['controller_ns']
        assert row['outer_ns'] >= row['controller_ns']
        assert row['physical'] == sum(detail['attempted_updates'].values())
    dense = []
    for tier in ('certified-1e-7', 'certified-1e-9'):
        for lifecycle in ('cold', 'prepared'):
            for lane in ([64, 1], [4, 2], [4, 4], [4, 8]):
                group = [r for r in rows if r['family'] == 'dense-rich-65'
                         and r['tier'] == tier and r['lane'] == lane and r['lifecycle'] == lifecycle]
                assert len(group) == 3 and all(r['certified'] for r in group)
                dense.append(dict(tier=tier, lifecycle=lifecycle, lane=lane,
                    cells=[r['result'] for r in group],
                    mean_outer_ms=statistics.mean(r['outer_ns'] / 1e6 for r in group),
                    median_outer_ms=statistics.median(r['outer_ns'] / 1e6 for r in group),
                    mean_gpu_ms=statistics.mean(r['gpu_us'] / 1000 for r in group),
                    physical=[r['physical'] for r in group],
                    phase_mean_ms={k: statistics.mean(r['costs_ns'][k] / 1e6 for r in group)
                                   for k in group[0]['costs_ns']},
                    outer_remainder_ms=statistics.mean((r['outer_ns'] - r['controller_ns']) / 1e6 for r in group),
                    coordination_ms=statistics.mean(details[r['id']]['coordination_within_transport_ns'] / 1e6 for r in group)))
    recovery_counts = Counter()
    certified_counts = Counter()
    all_restores_exact = True
    traces = []
    for row in rows:
        detail = details[row['id']]
        recoveries = []
        for index, event in enumerate(detail['events']):
            if 'reason' not in event:
                continue
            recovery_counts[event['reason']] += 1
            if row['certified']:
                certified_counts[event['reason']] += 1
            all_restores_exact &= event['restored_exact']
            preceding = detail['events'][index - 1]
            recovery = dict(event, lost_updates=preceding['logical'] - event['logical'])
            if event['reason'] == 'local_budget':
                audit = next((a for a in reversed(detail['audits']) if a['physical'] < event['physical']), None)
                if audit:
                    obs = audit['observation']
                    tolerance = 1e-7 if row['tier'] == 'certified-1e-7' else 1e-9
                    recovery['last_observation'] = obs
                    recovery['allowance'] = max(tolerance, min(1, obs['rho'])) / 64 * obs['scale']
                recovery['failed_window_count'] = preceding['count']
                recovery['flags'] = preceding['flags']
                recovery['window_warp_terms'] = [dict(zip(TERMS, preceding['local_terms'][i:i + 7]))
                                                for i in range(0, len(preceding['local_terms']), 7)]
            recoveries.append(recovery)
        if row['lifecycle'] != 'prepared' or row['rep'] != 0 or row['lane'] not in ([64, 1], [4, 4]):
            continue
        audits = []
        for audit in detail['audits']:
            cert = load(checked(audit['certificate']))
            audits.append(dict(physical=audit['physical'], logical=audit['logical'],
                observation=audit['observation'], accepted=audit['accepted'],
                feasible=cert['validation']['feasible'], gap_upper=cert['gap_upper'],
                gap_closed=cert['gap_closed'], refusal=cert['refusal'], certificate=audit['certificate']))
        traces.append(dict(family=row['family'], tier=row['tier'], lane=row['lane'],
            result=row['result'], physical=detail['physical_updates'], logical=detail['logical_updates'],
            attempted=detail['attempted_updates'], recoveries=recoveries, audits=audits))
    native_geometry = []
    for row in rows:
        if row['rep'] != 0 or row['lifecycle'] != 'prepared' or row['lane'] != [64, 1] or row['tier'] != 'certified-1e-9':
            continue
        detail = details[row['id']]
        checkpoint = load(checked(detail['final_checkpoint']))
        raw = checkpoint['terminal_export']['raw']
        _, data = model(row['family'])
        n = len(data['c'])
        p = (n + 31) // 32 * 32
        native_geometry.append(dict(family=row['family'], result=row['result'],
            target_distance_x=float(np.max(np.abs(np.asarray(raw[:n]) - data['target_x']))),
            target_distance_y=float(np.max(np.abs(np.asarray(raw[p:p+n]) - data['target_y']))),
            reencoding_x4=representation_error(raw, 4), reencoding_x8=representation_error(raw, 8)))
    sources = [Path(__file__), ROOT / 'tools/lp_fp4_integrate_run.py',
               ROOT / 'tools/lp_fp4_integrate_model.py', ROOT / 'tools/lp_fp4_recovery_contract.py',
               ROOT / 'research/lp-fp4-integrate/src/main.rs', ROOT / 'research/lp-fp4-integrate/src/checker.rs',
               ROOT / 'research/lp-fp4-integrate/cuda/integrate.cu', ROOT / 'research/lp-fp4-integrate/cuda/helpers.cuh']
    result = dict(schema_version=1, study=ref(STUDY), source_refs=[ref(p) for p in sources],
        scope='retained-record analysis and CPU re-encoding; no solver, checker or device execution',
        dense=dense, recovery_counts=dict(recovery_counts), certified_recovery_counts=dict(certified_counts),
        all_restores_exact=all_restores_exact, traces=traces, native_endpoint_geometry=native_geometry)
    put(output, result)
    return rows, details


def microprofile(rows, details, output):
    scratch = BASE / 'serialization-copies'
    scratch.mkdir(parents=True, exist_ok=False)
    measurements = []
    for family in ('dense-rich-65', 'coupled-equality'):
        for lane in ([64, 1], [4, 4]):
            row = next(r for r in rows if r['family'] == family and r['lane'] == lane
                       and r['tier'] == 'certified-1e-7' and r['lifecycle'] == 'prepared' and r['rep'] == 0)
            detail = details[row['id']]
            checkpoint_path = checked(detail['final_checkpoint'])
            model_path = checked(detail['model'])
            cert_path = checked(detail['certificate']['certificate'])
            payloads = {'model': load(model_path), 'checkpoint': load(checkpoint_path),
                        'certificate': load(cert_path), 'result': detail}
            for repetition in range(9):
                started = time.monotonic_ns()
                doc, _ = model(family)
                elapsed = time.monotonic_ns() - started
                assert doc == payloads['model']
                measurements.append(dict(family=family, lane=lane, repetition=repetition,
                    operation='model_construct', wall_ns=elapsed))
                for name, value in payloads.items():
                    started = time.monotonic_ns()
                    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
                    elapsed = time.monotonic_ns() - started
                    measurements.append(dict(family=family, lane=lane, repetition=repetition,
                        operation=name + '_json_encode', wall_ns=elapsed, bytes=len(raw)))
                    path = scratch / f'{family}-{lane[0]}-{name}-{repetition}.json'
                    started = time.monotonic_ns()
                    put(path, value)
                    elapsed = time.monotonic_ns() - started
                    measurements.append(dict(family=family, lane=lane, repetition=repetition,
                        operation=name + '_durable_put', wall_ns=elapsed, bytes=len(raw)))
                    assert path.read_bytes() == raw
    groups = sorted({(m['family'], tuple(m['lane']), m['operation']) for m in measurements})
    summary = []
    for family, lane, op in groups:
        group = [m for m in measurements if (m['family'], tuple(m['lane']), m['operation']) == (family, lane, op)]
        summary.append(dict(family=family, lane=list(lane), operation=op,
            median_ms=statistics.median(m['wall_ns'] / 1e6 for m in group),
            min_ms=min(m['wall_ns'] / 1e6 for m in group), max_ms=max(m['wall_ns'] / 1e6 for m in group),
            bytes=group[0].get('bytes')))
    put(output, dict(schema_version=1, source=ref(Path(__file__)), rows=measurements, summary=summary,
        scope='new CPU-only microprofile; not a decomposition of historical timing or a solver speedup',
        durable_put_includes_json_encoding=True, warm_order='9 repeats per family/lane, fixed operation order'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', action='store_true')
    args = parser.parse_args()
    rows, details = diagnosis(BASE / 'retained-analysis.json')
    if args.profile:
        microprofile(rows, details, BASE / 'host-serialization-profile.json')
    print(json.dumps(dict(cells=len(rows), gpu_jobs=0, solver_jobs=0, output=str(BASE))))


if __name__ == '__main__':
    main()
