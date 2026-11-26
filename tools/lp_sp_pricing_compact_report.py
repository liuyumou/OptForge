"""Aggregate the frozen compact study without repeating scientific cells."""
import argparse
import csv
import json
import re
import statistics
import subprocess
import sys
import unittest

from lp_sp_pricing_budget import BASE, ROOT, CPU, GPU, NS, accounting, binding, put
from lp_sp_pricing_compact_experiment import STUDY, validate
from lp_sp_pricing_gpu_opt_compare import read
from lp_sp_pricing_gpu_opt_report import bindings, pairs
from lp_sp_pricing_report import resource_summary
from lp_sp_pricing_finish import identities, still_same_process


def auxiliary(frozen):
    if not (STUDY / 'auxiliary-completed.json').exists():
        raise RuntimeError('auxiliary roster unfinished')
    rows = []
    for cell in frozen['auxiliary']:
        out = STUDY / 'auxiliary' / cell['id']
        proc = read(out / 'process.json')
        path = out / 'response.json'
        d = read(path) if path.exists() else {}
        metadata = d.get('metadata', {})
        batches = metadata.get('batches', [])
        # Two native staging slots are always allocated; CUDA context overhead is
        # excluded. Allocation formula is bound by the frozen native source.
        tile_bytes = ((128*256*24 + (128+256+2)*4 + 128 + 15)//16)*16
        state = max((b['state_bytes'] for b in batches), default=0)
        device = (metadata.get('gpu_arena_bytes') if cell['lane'] == 'wave'
                  else state + metadata.get('device_cache_bytes', 0) + 2*tile_bytes)
        complete = (proc['returncode'] == 0 and not proc['timed_out']
                    and d.get('status') == 'completed' and d.get('complete_labels', False))
        rows.append(dict(**{k:v for k,v in cell.items() if k != 'process_seconds'},
            process_allowance_seconds=cell['process_seconds'],
            status=d.get('status', 'missing_response'), reason=d.get('reason'),
            completed_labels=complete, labels=d.get('labels'), expected_labels=d.get('expected_labels'),
            matrix_positions=d.get('matrix_positions'), stored_factor_entries=d.get('stored_factor_entries'),
            process_seconds=proc['elapsed_ns']/NS, response_seconds=d.get('complete_ns', 0)/NS,
            process_hwm_bytes=d.get('process_hwm_bytes'), numerical_device_bytes=device,
            resident_searches=metadata.get('max_resident_searches', metadata.get('resident_searches')),
            batches=len(batches), advanced_searches=sum(b['width'] for b in batches)
                if batches else metadata.get('resident_searches', 0),
            checked_proposals=sum(b.get('proof', {}).get('checked', 0) for b in batches)
                if batches else metadata.get('proof', {}).get('checked_proposals', 0),
            exact_fallbacks=sum(b.get('proof', {}).get('exact_fallbacks', 0) for b in batches)
                if batches else metadata.get('proof', {}).get('gmp_fallbacks', 0),
            fallback_constructions=d.get('fallback_constructed'),
            response=binding(path) if path.exists() else None, process=binding(out / 'process.json')))
    groups = []
    for case, lane in sorted({(r['case'], r['lane']) for r in rows}):
        all_rows = [r for r in rows if r['case'] == case and r['lane'] == lane]
        accepted = [r for r in all_rows if r['completed_labels']]
        group = dict(case=case, lane=lane, slots=len(all_rows), complete=len(accepted))
        for key in ['process_seconds', 'response_seconds', 'process_hwm_bytes',
                    'numerical_device_bytes', 'resident_searches', 'advanced_searches', 'checked_proposals']:
            group['median_'+key] = statistics.median(r[key] for r in accepted) if accepted else None
        groups.append(group)
    comparisons = []
    indexed = {(r['case'], r['repetition'], r['lane']): r for r in rows}
    for case in sorted({r['case'] for r in rows}):
        for left in ['wave', 'compact-serial', 'compact-stream']:
            ratios = []
            for rep in range(2):
                a = indexed.get((case, rep, left)); b = indexed.get((case, rep, 'compact-pipeline'))
                if a and b and a['completed_labels'] and b['completed_labels']:
                    ratios.append(a['process_seconds']/b['process_seconds'])
            if ratios:
                comparisons.append(dict(case=case, left=left, right='compact-pipeline', pairs=len(ratios),
                    median_left_over_right=statistics.median(ratios), ratios=ratios))
    return rows, groups, comparisons


def report(identity):
    frozen = validate(); out = BASE / identity; out.mkdir(exist_ok=False)
    audited = read(STUDY / 'audits.json'); rows = audited['small']
    if len(rows) != len(frozen['small']) or {r['id'] for r in rows} != {r['id'] for r in frozen['small']}:
        raise RuntimeError('small roster mismatch')
    if {r['model'] for r in audited['large']} != {r['name'] for r in frozen['original_models']}:
        raise RuntimeError('large roster mismatch')
    aux, groups, comparisons = auxiliary(frozen)
    lanes = {lane: dict(slots=len(subset), timely_exact=sum(r['timely'] and r['exact_accepted'] for r in subset),
        timely_strict=sum(r['timely'] and r['strict_accepted'] for r in subset),
        total_complete_seconds=sum(r['complete_ns'] for r in subset)/NS)
        for lane in ('wave', 'compact-cpu', 'compact-serial', 'compact-pipeline')
        for subset in [[r for r in rows if r['lane'] == lane]]}
    paired = [pairs(rows, left, 'compact-pipeline', tier)
              for tier in ('exact', 'strict') for left in ('wave', 'compact-cpu', 'compact-serial')]
    large = []
    for row in audited['large']:
        d = read(row['response']['path']) if row['response'] else {}
        large.append(dict(**row, native_seconds=d.get('solve_ns', 0)/NS,
            process_hwm_bytes=d.get('process_hwm_bytes'), storage_peak_entries=d.get('storage_peak_entries'),
            work=d.get('work'), internal_exact_accepted=d.get('audit', {}).get('accepted', False)))
    result = dict(status='compact_experiments_audited', freeze=binding(STUDY/'freeze.json'),
        audits=binding(STUDY/'audits.json'), auxiliary=aux, auxiliary_groups=groups,
        auxiliary_comparisons=comparisons, small=rows, lanes=lanes, small_comparisons=paired, original=large,
        checked_bindings=bindings(audited)+bindings(aux), resources=resource_summary(),
        limitations=['Opt-in practical variant; no literal-reference completion or strongly polynomial claim.',
            'Auxiliary comparisons use the same requested labels, but different pruning and actual work.',
            'Only two cold repetitions; caches are not flushed; limited synthetic fixtures.',
            '128 million positions are represented by 4000 positive-factor entries and 8000 actual nonzeros.',
            'Process HWM and explicit numerical device allocations exclude aggregate device context overhead.',
            'No new COPT cells; no transitive COPT superiority claim.'])
    put(out/'result.json', result)
    docs = ROOT/'docs/benchmarks'
    (docs/'lp-sp-pricing-compact-results.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    with (docs/'lp-sp-pricing-compact-auxiliary.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(groups[0])); writer.writeheader(); writer.writerows(groups)
    lines = ['# Compact geometry and bounded GPU searches', '',
        'The opt-in compact path implements lazy exact fallback, tiled products and checks, bounded synchronized batches, and implicit paired bases. It removes the old dimension-only rejection for the three original million-nonzero LPs. All three reach their 20-second deadline in CPU geometry construction before an auxiliary query; none returns a certificate. Memory admission and complete-solve performance are separate outcomes.', '',
        'See the [complete evidence](lp-sp-pricing-compact-results.json), [auxiliary CSV](lp-sp-pricing-compact-auxiliary.csv), [settled checkpoint](lp-sp-pricing-compact-checkpoint.json), [prospective plan](../plans/lp-sp-pricing.md#compact-geometry-and-bounded-gpu-execution), and [historical COPT/million study](lp-sp-pricing-million.md).', '',
        '## Implementation', '',
        'The isolated entry point is `tools/lp_sp_pricing_compact_run.py MODEL OUTPUT`. It accepts the canonical rational model or portable CSR input; `--cpu` disables GPU proposals and `--serial` disables cross-batch overlap. Run it through the existing study reservation wrapper with a fresh identity. Existing solver defaults and historical numerical sources are unchanged.', '',
        '- CPU constraints and exact tableaus are allocated only if GPU proposals leave labels unresolved. The existing one-million-cell fallback/recovery limit still applies.',
        '- Sparse RREF factors represent the positive space; its orthogonal complement `[-R^T I]` and paired identity blocks are generated on demand. Exact calibration and recovery use sparse products. Actual elimination fill, bit growth and deadlines remain bounded.',
        '- Each GPU batch holds at most 32 searches in this configuration. Searches advance in common PDHG steps and reuse coefficients across four right-hand sides. Numerical state is capped at 256 MiB; the selected device tile cache is 64 MiB.',
        '- Matrices beyond the tile cache use two pinned upload slots, two copy streams and explicit events. One producer prepares the next tile. At most one host proof overlaps the next GPU batch; redundant work already launched is recorded.',
        '- Streamed rigorous interval checks use bounded coefficient/check caches of 32 MiB each. Uncertain proposals use exact rational products; only proved labels are accepted. Original endpoint checks remain independent and strict at 1e-9.', '',
        '## Auxiliary completion and memory', '',
        'The frozen seed-122009 roster contains 18 cold processes and 64 FP64 steps per launched batch. Dense-million has 1,000,000 nonzeros. Diagonal-million has 1,000,000 positions but only 500 nonzeros. Factor-128m has 128,000,000 positions, 4000 stored positive-factor entries and 8000 paired nonzeros. Every returned label is checked against an independent exact structural witness or a dense common positive witness.', '',
        '| Case | Lane | Complete / slots | Cold process s | Process HWM MiB | Numerical device MiB | Resident searches |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for g in groups:
        if not g['complete']:
            lines.append(f"| {g['case']} | {g['lane']} | 0 / {g['slots']} | — | — | — | — |")
        else:
            lines.append(f"| {g['case']} | {g['lane']} | {g['complete']} / {g['slots']} | {g['median_process_seconds']:.3f} | {g['median_process_hwm_bytes']/2**20:.1f} | {g['median_numerical_device_bytes']/2**20:.2f} | {g['median_resident_searches']:.0f} |")
    lines += ['', 'Values are medians of two repetitions. Cold process time includes fixture generation, initialization, upload, iterations, label checks, teardown and publication. It is auxiliary label-completion time, not original-LP solution time. The previous wave control constructs its packed basis/checker directly and does not construct a CPU fallback tableau. Lazy fallback savings are therefore not credited to this timing comparison.', '',
        'Numerical device memory counts the wave arena or compact state, cache and two staging buffers. It excludes CUDA context/library/graph allocations; this is an allocation calculation, not a sampled whole-device peak. Process HWM is measured separately and includes input/factors, caches and runtime. Old wave is unsupported for factor-128m and is not run there.', '',
        '| Case | Baseline / pipeline | Matched cold-time ratio |',
        '| --- | --- | ---: |']
    for c in comparisons:
        lines.append(f"| {c['case']} | {c['left']} / compact-pipeline | {c['median_left_over_right']:.3f}× |")
    lines += ['', 'Ratios above one favor the pipeline. These are time-to-label-completion comparisons with unequal work: wave advances all targets, while compact prunes between batches; pipelining can launch one redundant batch. Actual advanced and checked counts remain in the JSON/CSV. Dense forced streaming retains the same bounded state but repeats transfers; the cached path is faster. No kernel-only speedup is inferred from advancement timers that include transfer/stream waits.', '',
        '## Original million-nonzero attempts', '',
        'These are the exact three previously unsupported inputs, seed 121951, one attempt each. The new path receives 20 native seconds and 30 process seconds. The preceding dimension-only refusals and COPT results remain historical; no COPT solve is repeated.', '',
        '| Model | Result | Native s | Process HWM MiB | Queries | Strict certificate |',
        '| --- | --- | ---: | ---: | ---: | --- |']
    for r in large:
        lines.append(f"| {r['model']} | {r['status']}: {r['reason']} | {r['native_seconds']:.3f} | {r['process_hwm_bytes']/2**20:.1f} | {r['queries']} | {r['strict_accepted']} |")
    lines += ['', 'All three stay near 258–268 MiB process HWM during their bounded attempts. This is not a forecast of full-solve memory: sparse exact elimination may fill and rational numerators/denominators grow. The recorded `geometry_and_experts` phase includes sparse row reduction, initial calibration bounds and expert setup; the existing phase timer does not isolate those substeps. No query is reached, so GPU auxiliary acceleration cannot improve these observed attempts. Fraction-free/modular exact elimination or a further implicit calibration design would need separate implementation and numerical admission.', '',
        '## Fresh end-to-end checks', '',
        'Seed 122011 supplies coupled, dense and degenerate models with eight columns and sixteen rows. Four lanes, two cyclic repetitions and identical 10/15-second native/process allowances give 24 cold cells. Complete cost includes model encoding, cold process startup and preparation, solve/check/recovery, teardown and the external exact plus strict endpoint audit.', '',
        '| Lane | Slots | Timely exact | Timely strict | Total complete s |',
        '| --- | ---: | ---: | ---: | ---: |']
    for lane, d in lanes.items():
        lines.append(f"| {lane} | {d['slots']} | {d['timely_exact']} | {d['timely_strict']} | {d['total_complete_seconds']:.3f} |")
    lines += ['', '| Tier | Baseline / pipeline | Jointly timely repetitions | Median complete ratio |',
        '| --- | --- | ---: | ---: |']
    for p in paired:
        ratio='—' if p['median_left_over_right'] is None else f"{p['median_left_over_right']:.3f}×"
        lines.append(f"| {p['tier']} | {p['left']} / compact-pipeline | {p['paired_repetitions']} | {ratio} |")
    lines += ['', 'All 24 endpoints pass the independent exact rational original-model verifier. The unchanged floating endpoint checker reports primal feasibility but no finite dual bound for these free-variable models, so strict acceptance is 0/24. Exact and strict tiers are kept separate; no strict ratio is available.', '',
        'Uncertified, failed or late outcomes stay visible and are excluded from certified ratios. These few synthetic models do not establish broad superiority or a COPT speedup. The practical candidate has no strongly polynomial complexity claim.', '',
        '## Validation and accounting', '',
        'Final numerical admission covers 24 GPU configurations, 116 exact proposals, independent scalar equations, serial/pipeline equivalence, cached/forced-streaming dense/CSR paths, and all four CUDA sanitizers. Native ASan/UBSan covers 64 cases. Eleven compact integration tests cover sparse RREF/complements, calibration equivalence, lazy fallback and its refusal, bounded caches, interval/exact agreement, and original optimal/infeasible/unbounded certificates.', '',
        'The final study suite and documentation receipt are bound in the settled checkpoint. The initial CPU admission test-import error retains its full 960 CPU-second charge. All preceding failures, source snapshots, budgets and resource guards remain. This study uses four slots, a 16-GiB sampled host reservation, fresh 30-second GPU idle checks and the existing 240000 CPU / 30000 GPU-second allocation. All scientific cells are attempted once.', '']
    (docs/'lp-sp-pricing-compact.md').write_text('\n'.join(lines))
    return result


def verify_all(identity):
    report(identity)
    for path in (ROOT/'tools').glob('lp_sp_pricing_compact*.py'):
        compile(path.read_text(), str(path), 'exec')
    suite = unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'), 'test_lp_sp_pricing*.py')
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    if not outcome.wasSuccessful() or outcome.skipped or outcome.testsRun != 83:
        raise RuntimeError('incomplete final tests')
    docs = subprocess.run([sys.executable, '-B', str(ROOT/'tools/build_docs.py')], check=True,
        cwd=ROOT, text=True, capture_output=True)
    print(docs.stdout, end='', flush=True)
    match = re.search(r'documentation built: (\d+) pages', docs.stdout)
    if not match: raise RuntimeError('missing documentation receipt')
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    put(BASE/identity/'verification.json', dict(status='passed', tests=outcome.testsRun,
        documentation_pages=int(match[1]), result=binding(BASE/identity/'result.json'),
        outputs=[binding(ROOT/'docs/benchmarks'/name) for name in ['lp-sp-pricing-compact.md',
            'lp-sp-pricing-compact-results.json', 'lp-sp-pricing-compact-auxiliary.csv']]))


def settle(identity, reservation):
    validate(); verification=BASE/identity/'verification.json'; bindings(read(verification))
    summary=resource_summary()
    if summary['pending_at_snapshot']: raise RuntimeError('active reservation')
    receipt=BASE/'resources'/(reservation+'.settlement.json')
    if read(receipt)['status'] != 'passed': raise RuntimeError('verification supervision failed')
    cpu,gpu=accounting(BASE),accounting(BASE,True)
    if any(cpu[p]>CPU[p]*NS or gpu[p]>GPU[p]*NS for p in CPU): raise RuntimeError('phase cap')
    owned=set()
    for pattern in ('*.resource.json','*.journal.json'):
        for path in (BASE/'resources').glob(pattern): owned.update(identities(read(path)))
    if any(still_same_process(*item) for item in owned): raise RuntimeError('owned process remains')
    checkpoint=dict(status='compact_study_settled',resources=summary,cpu_phase_ns=cpu,gpu_phase_ns=gpu,
        verification=binding(verification),reporting_settlement=binding(receipt),
        tests=read(verification)['tests'],documentation_pages=read(verification)['documentation_pages'],
        owned_identities=len(owned),live_owned_identities=[],active_reservations=[])
    put(BASE/identity/'settled-checkpoint.json',checkpoint)
    target=ROOT/'docs/benchmarks/lp-sp-pricing-compact-checkpoint.json'
    target.write_text(json.dumps(checkpoint,indent=2,sort_keys=True)+'\n')
    (ROOT/'book/docs/benchmarks'/target.name).write_bytes(target.read_bytes())
    print(json.dumps(dict(status=checkpoint['status'],cpu_seconds=summary['cpu_ns']/NS,
        gpu_seconds=summary['gpu_ns']/NS,owned_identities=len(owned))),flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['verify','settle'])
    p.add_argument('identity');p.add_argument('--reservation');a=p.parse_args()
    if a.action=='verify':verify_all(a.identity)
    else:settle(a.identity,a.reservation)
