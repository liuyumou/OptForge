"""Complete, preparation-inclusive larger-scale comparison and proof receipt."""
import argparse
import csv
import datetime as dt
import json
import re
import subprocess
import sys
import unittest
from lp_sp_pricing_budget import ROOT, BASE, NS, put, binding, accounting
from lp_sp_pricing_scale_budget import CPU, GPU, allocation
from lp_sp_pricing_scale_experiment import STUDY, validate
from lp_sp_pricing_scale_long import STUDY as LONG, validate as validate_long
from lp_sp_pricing_scale_challenge import RESULT as CHALLENGE
from lp_sp_pricing_scale_reconstruct import STUDY as RECON, validate as validate_reconstruction
from lp_sp_pricing_scale_seal import RESULT as SEAL, checked as checked_seal
from lp_sp_pricing_gpu_opt_compare import read
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_report import resource_summary
from lp_sp_pricing_finish import identities, still_same_process


def seconds(value):
    return '—' if value is None else f'{value/NS:.3f}'


def status(row):
    value = row['status']
    return {1: 'numerical optimum', 8: 'time limit', 10: 'interrupted'}.get(value, str(value))


def report(identity):
    frozen = validate(); longer = validate_long(); validate_reconstruction(); approval = allocation()
    failed_group = checked_seal(); excluded = set(failed_group['timing_excluded_ids'])
    settlements = []
    for name in ['scale-certificate-admit-v1', 'scale-freeze-v1', 'scale-challenge-v1',
                 'scale-long-freeze-v1', 'scale-long-gpu-v1', 'scale-long-auto-v1', 'scale-long-audit-v1',
                 'scale-reconstruction-admit-v1', 'scale-reconstruction-v1', 'scale-gpu-group-1-seal-v1'] + [
            f'scale-{kind}-group-{group}-v1' for group in (0, 1) for kind in ('gpu', 'auto', 'audit')]:
        path = BASE/'resources'/(name+'.settlement.json')
        receipt = read(path)
        if name == 'scale-gpu-group-1-v1':
            if receipt['status'] != 'refused' or receipt['overrun'] or not receipt['cleanup_empty']:
                raise ValueError('original failed group changed')
        elif receipt['status'] != 'passed' or receipt['overrun'] or not receipt['cleanup_empty']:
            raise ValueError('new campaign supervision requires an explicit disposition: '+name)
        settlements.append(binding(path))
    audits = [read(STUDY/f'audits-group-{g}.json') for g in (0, 1)]
    rows = [r for audit in audits for r in audit['rows']]
    expected = {c['id'] for c in frozen['cells']}
    if len(rows) != 30 or {r['id'] for r in rows} != expected:
        raise ValueError('incomplete or duplicated comparison roster')
    accepted_ids = {r['id'] for r in rows if r['lane'] == 'candidate' and r['independent_exact_accepted']}
    for r in rows:
        r['native_allowance_seconds'] = 120
    extra_audit = read(LONG/'audits.json')
    extra = extra_audit['rows']
    if len(extra) != 9 or {r['id'] for r in extra} != {c['id'] for c in longer['cells']}:
        raise ValueError('incomplete supplement roster')
    for kind in ('gpu', 'auto'):
        if read(LONG/f'{kind}-completed.json')['status'] != 'all_slots_disposed':
            raise ValueError('unfinished supplement group')
    for r in extra:
        r['native_allowance_seconds'] = 300
    rows += extra
    for row in rows:
        row['observed_native_timely'] = row['timely']
        row['timing_eligible'] = row['id'] not in excluded
        row['timely'] = row['timely'] and row['timing_eligible']
    reconstruction = read(RECON/'result.json')
    if (reconstruction['status'] != 'all_endpoints_disposed' or len(reconstruction['rows']) != len(rows)
            or {r['id'] for r in reconstruction['rows']} != {r['id'] for r in rows}):
        raise ValueError('incomplete common-reconstruction roster')
    for g in (0, 1):
        for kind in ('gpu', 'auto'):
            if read(STUDY/f'{kind}-group-{g}-completed.json')['status'] != 'all_slots_disposed':
                raise ValueError('unfinished solver group')
    challenge = read(CHALLENGE)
    if challenge['status'] != 'passed':
        raise ValueError('large certificate challenge incomplete')
    challenged_ids = {r['id'] for r in challenge['checks']}
    if challenged_ids != accepted_ids or challenge['mutation_checks'] != 2*len(accepted_ids):
        raise ValueError('challenge coverage differs from all accepted candidate endpoints')
    phases = []
    for row in rows:
        response = read(row['response']['path']) if row.get('response') else {}
        proof = read(row['independent_proof']['path']) if row.get('independent_proof') else {}
        if row['independent_exact_accepted']:
            if (not proof.get('accepted') or proof.get('visited_nonzeros') != row['nonzeros']
                    or not proof.get('primal_feasible') or not proof.get('dual_equations')
                    or not proof.get('zero_gap')):
                raise ValueError('accepted exact proof lacks full original-model traversal')
        phases.append(dict(id=row['id'], input_ns=response.get('input_ns'),
            proposal=response.get('proposal'), geometry=response.get('geometry_diagnostics'),
            phase_ns=response.get('phase_ns'), vendor_profile=response.get('profile'),
            parameters=response.get('parameters'), automatic_defaults=response.get('automatic_defaults'),
            process_hwm_bytes=response.get('process_hwm_bytes'), queries=response.get('queries'),
            gpu_confirmed=response.get('gpu_confirmed'), independent_arithmetic_ns=proof.get('elapsed_ns')))
    pairs = []
    for model in frozen['models']+longer['models']:
        pair = {r['lane']: r for r in rows if r['family'] == model['name'] and r['seed'] == model['seed']}
        for vendor in ('copt-gpu', 'copt-auto'):
            a, b = pair['candidate'], pair[vendor]
            strict = all(r['timely'] and r['strict_accepted'] for r in (a, b))
            exact = all(r['timely'] and r['independent_exact_accepted'] for r in (a, b))
            pairs.append(dict(family=model['name'], seed=model['seed'], vendor=vendor,
                jointly_timely_strict=strict, jointly_timely_exact=exact,
                operational_copt_over_candidate=b['operational_complete_ns']/a['operational_complete_ns'] if strict else None,
                fully_audited_copt_over_candidate=b['complete_ns']/a['complete_ns'] if exact else None))
    counts = {}
    for allowance in (120, 300):
        counts[str(allowance)] = {}
        for lane in ('candidate', 'copt-gpu', 'copt-auto'):
            group = [r for r in rows if r['lane'] == lane and r['native_allowance_seconds'] == allowance]
            counts[str(allowance)][lane] = dict(slots=len(group), attempted=sum(r['status'] != 'unattempted_wall_budget' for r in group),
                returned=sum(r.get('response') is not None for r in group),
                vendor_numerical_optima=sum(r['status'] == 1 for r in group),
                strict_accepted=sum(r['strict_accepted'] for r in group),
                independent_exact_accepted=sum(r['independent_exact_accepted'] for r in group),
                timely_strict=sum(r['timely'] and r['strict_accepted'] for r in group),
                timely_exact=sum(r['timely'] and r['independent_exact_accepted'] for r in group))
    hardware_log = STUDY/'runs/dense-4m-122301-copt-gpu/copt.log'
    hardware_text = hardware_log.read_text()
    hardware = dict(cpu=re.search(r'The CPU model is (.+)', hardware_text)[1],
        copt_version=re.search(r'Using Cardinal Optimizer v([^ ]+)', hardware_text)[1],
        gpu=re.search(r'GPU 0: (.+) \(CUDA capability', hardware_text)[1],
        evidence=binding(hardware_log), cpu_slots=4, candidate_blas_threads=1, copt_threads=4)
    result = dict(status='larger_comparison_and_longer_window_supplement_audited',
        hardware=hardware,
        freeze=binding(STUDY/'freeze.json'), allocation=binding(BASE/'scale-allocation-v1.json'),
        supplement_freeze=binding(LONG/'freeze.json'), supplement_audit=binding(LONG/'audits.json'),
        supplement_disclosure=longer['disclosure'],
        common_reconstruction=reconstruction,
        failed_group_disposition=binding(SEAL), timing_excluded_ids=sorted(excluded),
        audits=[binding(STUDY/f'audits-group-{g}.json') for g in (0, 1)],
        certificate_admission=binding(BASE/'scale-certificate-admit-v1/admission.json'),
        campaign_settlements=settlements,
        challenge=binding(CHALLENGE), rows=rows, phases=phases, pairs=pairs, counts=counts,
        checked_bindings=bindings(audits)+bindings(extra_audit)+bindings(challenge)+bindings(frozen)+bindings(longer)+bindings(reconstruction),
        resources=resource_summary(), limits=longer['limitations'],
        timing_scope=dict(operational='encoding + cold process + unchanged strict audit',
            fully_audited='operational + cold independent arbitrary-precision audit',
            excluded='resource idle/admission/settlement; separate corruption challenges',
            native_seconds=[120, 300], process_seconds=[150, 360]),
        report_utc=dt.datetime.now(dt.timezone.utc).isoformat(), wall_deadline_utc=approval['wall_deadline_utc'])
    out = BASE/identity; out.mkdir(exist_ok=False); put(out/'result.json', result)
    docs = ROOT/'docs/benchmarks'
    (docs/'lp-sp-pricing-scale-results.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    columns = ['id', 'family', 'seed', 'lane', 'native_allowance_seconds', 'nonzeros', 'status', 'reason', 'route',
               'timely', 'observed_native_timely', 'timing_eligible',
               'strict_accepted', 'independent_exact_accepted', 'native_ns', 'process_ns',
               'encoding_ns', 'strict_audit_ns', 'independent_audit_ns', 'operational_complete_ns', 'complete_ns']
    with (docs/'lp-sp-pricing-scale-comparison.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader()
        writer.writerows({k:r.get(k) for k in columns} for r in rows)
    reconstruction_columns = ['id', 'family', 'seed', 'lane', 'native_allowance_seconds', 'timely',
        'observed_native_timely', 'timing_eligible', 'raw_strict_accepted', 'accepted', 'reason', 'process_ns', 'strict_audit_ns', 'independent_audit_ns',
        'operational_complete_ns', 'complete_ns']
    with (docs/'lp-sp-pricing-scale-reconstruction.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=reconstruction_columns); writer.writeheader()
        writer.writerows({k:r.get(k) for k in reconstruction_columns} for r in reconstruction['rows'])
    lines = ['# Larger-scale LP evaluation and certificate assurance', '',
        'Thirteen fresh models contain 4–16 million nonzeros each. The primary roster has two independent seeds across five families and three solver lanes, for thirty slots with 120 native / 150 process seconds per solver. A separately frozen third seed covers three families with 300 native / 360 process seconds, adding nine slots. All thirty-nine slots, deadlines and missing endpoints remain visible.', '',
        'See the [complete results](lp-sp-pricing-scale-results.json), [all thirty-nine cells](lp-sp-pricing-scale-comparison.csv), [settled checkpoint](lp-sp-pricing-scale-checkpoint.json), and [preceding million-scale diagnosis](lp-sp-pricing-geometry.md).', '',
        '## Outcomes', '',
        '| Native allowance | Lane | Returned / slots | Vendor numerical optima | Strict accepted | Independent exact accepted | Timely exact with eligible timing |',
        '| ---: | --- | ---: | ---: | ---: | ---: | ---: |']
    for allowance, lanes in counts.items():
        for lane, c in lanes.items():
            numerical = '—' if lane == 'candidate' else str(c['vendor_numerical_optima'])
            lines.append(f"| {allowance} s | {lane} | {c['returned']}/{c['slots']} | {numerical} | {c['strict_accepted']} | {c['independent_exact_accepted']} | {c['timely_exact']} |")
    lines += ['', 'A vendor numerical optimum, unchanged original-model 1e-9 acceptance, and independent exact rational acceptance are distinct outcomes. In free-variable models, a small nonzero dual residual can prevent a finite rigorous dual bound. Rejection by a stronger certificate check does not establish that a numerical optimum is wrong.', '',
        '## Workload and controls', '',
        f"Recorded hardware is {hardware['cpu']} and {hardware['gpu']}; the installed vendor is COPT {hardware['copt_version']}. The supervisor permits four CPU slots. Candidate BLAS is limited to one thread and COPT is configured for four threads.", '',
        '| Family | Rows × columns | Nonzeros per input | Structure |', '| --- | ---: | ---: | --- |']
    for model in frozen['models'][:5]:
        shape = '20% inactive rows' if model['mixed'] else ('row scaling 2^-4 to 2^4' if model['scaled'] else 'all rows active')
        lines.append(f"| {model['name']} | {model['m']} × {model['n']} | {model['nonzeros']:,} | {shape} |")
    lines += ['',
        'Seeds 122301 and 122357 are separate inputs, not repeated timings of the same input. Matrices have signed short-dyadic coefficients, nonuniform planted primal coordinates and dual weights, and a cyclic sparse pattern where applicable. Construction witnesses pass the original strict checker and are never passed to the solvers. Eight inputs are square and all-active; two are rectangular with inactive inequalities. This structure can favor exact reconstruction.', '',
        'The longer-window supplement uses fresh seed 122419 for dense-16m, sparse-scaled-10m and mixed-tall-4m. It was added after some primary outcomes were visible, to allow longer completion attempts on the larger dense/sparse and rectangular families. Candidate code and vendor settings remain unchanged. It repeats no attempted LP. Its 300-second results remain a separate cohort; medians and claims are not pooled across different deadlines.', '',
        'The candidate uses the new guarded certificate boundary with the previously admitted numerical code. Its exact-certified factor presolve runs on CPU; a successful presolve does not initialize CUDA. Unsuccessful presolve proceeds to the existing GPU-capable geometry/pricing path under unchanged operation, fill and arithmetic limits. This is an opt-in practical candidate, not evidence that the full paper algorithm is implemented or strongly polynomial.', '',
        'COPT GPU uses the retained scale-off GPU-PDLP configuration: LpMethod=6, Presolve=0, Scaling=0, Crossover=0, PDLPTol=1e-12. COPT auto uses automatic CPU LP-method selection and the installed default presolve, scaling, dualization and crossover. Both are configured for four CPU threads, unchanged original coefficients, MatrixTol=0 and 1e-9 primal/dual tolerances. Exact returned parameters and defaults are retained. Candidate/GPU-COPT order alternates across families and seeds; CPU-auto runs in separate groups. Candidate BLAS remains single-threaded under the existing supervisor. No settings were retuned after new outcomes were observed.', '',
        '## Complete timings', '',
        'Operational complete time includes common model encoding, cold process startup, input/hash checks, CSR conversion, factorization or GPU preparation, solving, internal certificate work, endpoint writing, teardown, and the unchanged cold strict audit. Fully audited time additionally includes a separate cold arbitrary-precision certificate process. COPT internal GPU setup remains within its opaque solve call. Resource admission, idle observations and settlement are charged separately; corruption challenges are additional research validation and excluded from both timings.', '',
        'Times for unsuccessful cells are time to their recorded disposition, not certified solution times. There is one cold process per input/lane, without cache flushing. The model encoding measurement is shared consistently across all three lanes for that input.', '',
        'The second candidate/GPU group wrote all ten process results and its completion marker, but final resource supervision failed with `coordinator_lost`. Its full 6240 CPU / 1560 GPU-second charge remains, with empty cleanup and no recorded overrun. A separately supervised read-only seal verifies retained records and recorded process absence; it does not regrade supervision. The preceding cause is unknown. All ten timings remain descriptive and are excluded from timely certified counts and every raw/reconstructed speedup ratio. Their mathematical certificates still require the complete independent audits. The separate second-seed automatic-CPU controls are unaffected.', '',
        '| Family | Seed | Allowance s | Lane | Result | Native s | Operational complete s | Fully audited s | Timely strict / exact |',
        '| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- |']
    for r in rows:
        accepted = f"{r['timely'] and r['strict_accepted']} / {r['timely'] and r['independent_exact_accepted']}"
        lines.append(f"| {r['family']} | {r['seed']} | {r['native_allowance_seconds']} | {r['lane']} | {status(r)} | {seconds(r.get('native_ns'))} | {seconds(r.get('operational_complete_ns'))} | {seconds(r.get('complete_ns'))} | {accepted} |")
    strict_pairs = sum(p['jointly_timely_strict'] for p in pairs)
    exact_pairs = sum(p['jointly_timely_exact'] for p in pairs)
    lines += ['', f'There are {strict_pairs}/{len(pairs)} jointly timely strict pairs and {exact_pairs}/{len(pairs)} jointly timely exact pairs in the raw-endpoint comparison. Ratios are retained only at their corresponding common acceptance tier; failures and time limits do not become speedup ratios.', '',
        '## Common endpoint reconstruction', '',
        'Raw COPT endpoints and the candidate do not use the same certificate representation. A separately frozen, post-hoc diagnostic therefore applies the candidate\'s same bounded dyadic quantization ladder (exponents 0–24, integer bound 2^40) to every available endpoint from all lanes. Floating screens only reject proposals; the guarded exact checker, unchanged strict checker and independent arbitrary-precision checker must all accept. No factorization, LP solve or planted witness is used. Missing endpoints remain unsuccessful. Original results are preserved.', '',
        'This alternative complete pipeline retains original model encoding and cold solver-process time, then adds a cold reconstruction process and fresh strict/exact audits. It replaces the raw endpoint audit in the pipeline cost; all actual research work, including both audit pathways, remains charged in resource accounting. The same extra work is charged to candidate and vendor outputs. Reconstruction is bounded by 60 work / 90 process seconds. Its 32 valid perturbed-endpoint tests and 32 negative-dual tests pass before use.', '',
        'See [all reconstruction outcomes](lp-sp-pricing-scale-reconstruction.csv). This tier measures COPT plus shared certificate reconstruction, not native COPT certification, and was specified after first-seed raw audit outcomes were visible.', '',
        '| Family | Seed | COPT lane | Both timely exact after reconstruction | COPT / candidate operational | COPT / candidate fully audited |',
        '| --- | ---: | --- | --- | ---: | ---: |']
    for pair in reconstruction['pairs']:
        operational = '—' if pair['operational_copt_over_candidate'] is None else f"{pair['operational_copt_over_candidate']:.3f}×"
        fully = '—' if pair['fully_audited_copt_over_candidate'] is None else f"{pair['fully_audited_copt_over_candidate']:.3f}×"
        lines.append(f"| {pair['family']} | {pair['seed']} | {pair['vendor']} | {pair['jointly_timely_exact']} | {operational} | {fully} |")
    common_counts = {lane:sum(r['accepted'] for r in reconstruction['rows'] if r['lane'] == lane)
                     for lane in ('candidate', 'copt-gpu', 'copt-auto')}
    lines += ['', f"Common reconstruction accepts {common_counts['candidate']} candidate, {common_counts['copt-gpu']} GPU-COPT and {common_counts['copt-auto']} automatic-CPU COPT endpoints. The excluded supervision group remains excluded from all ratios.", '']
    for pair in reconstruction['pairs']:
        if not pair['jointly_timely_exact']:
            continue
        matched = {r['lane']:r for r in reconstruction['rows'] if r['family'] == pair['family'] and r['seed'] == pair['seed']}
        a, b = matched['candidate'], matched[pair['vendor']]
        lines += [f"On {pair['family']} seed {pair['seed']}, the candidate and {pair['vendor']} complete the common fully audited pipeline in {a['complete_ns']/NS:.3f} and {b['complete_ns']/NS:.3f} seconds, respectively ({pair['fully_audited_copt_over_candidate']:.3f}×). This is a single eligible same-input pair on a synthetic all-active square LP; it is not broad solver or GPU superiority.", '']
    lines += ['',
        '## Certificate reliability', '',
        'The additional checker decodes original binary64 coefficients using `float.as_integer_ratio`, decodes rational endpoints independently, and traverses the entire original CSR with Python arbitrary-precision integer arithmetic. It checks every primal inequality, every dual equation, dual nonnegativity and exact zero gap. It also checks that published floating endpoints match the rational proof. It shares neither the native signed-128 arithmetic kernel nor solver acceptance reductions, and it does not use a planted witness. Original content chunks are hash-verified when read.', '',
        'Admission compares 128 randomized mixed-active valid cases with two independent oracles and rejects 384 deliberately invalid certificates. Boundary tests cover large cancellation, range/exponent limits, non-dyadic rational proofs, modified immutable chunks, forged integer caches and a one-ULP disagreement between published and rational endpoints.', '',
        'The tests exposed an unsigned-narrowing issue in the old direct helper: uint64(2^64-1) could become signed -1 before its range check. The new opt-in boundary checks original-dtype ranges before conversion and verifies cached integers against the original coefficients. Previous actual solver proposals were bounded signed integers; old sources, receipts and timings remain unchanged.', '',
        f"Every one of the {len(accepted_ids)} accepted candidate endpoints in the primary cohort also receives two deliberately invalid large-model challenges. Both native and independent checkers reject all {challenge['mutation_checks']} challenges. The objective mutation receives a complete original-matrix traversal; the negative-dual mutation is rejected by the sign condition. The supplement receives the same full independent endpoint proof, but is outside that earlier frozen corruption-challenge roster. No solver is rerun and immutable inputs are not changed.", '',
        'Exact proof validity is deterministic for the represented input. Broader tests and an independent arithmetic implementation improve confidence in the software; they do not turn a certificate into a statistical claim. The proof is about the stored coefficients, not unknown real-world data before rounding.', '',
        '## Scope and resource settlement', '',
        'The two-hour wall deadline and phase transfer were recorded before model generation. Existing total ceilings remain 240000 CPU / 30000 GPU seconds. Four CPU slots, physical host/GPU/storage caps, ownership checks, idle admission and all original failure charges remain in force. The compact checkpoint records actual settled charges, final tests/documentation and the absence of owned processes. No historical scientific cell is repeated.', '',
        'This is a larger synthetic capacity and certificate evaluation. It does not establish broad LP or GPU superiority. Fast CPU factor presolve, expensive rectangular exact geometry, and unsuccessful vendor endpoints must be interpreted separately. Two seeds do not characterize timing variance or a broad workload distribution. Candidate process high-water memory is retained; no matched COPT process-memory comparison is claimed.', '']
    (docs/'lp-sp-pricing-scale.md').write_text('\n'.join(lines))


def verify_all(identity):
    report(identity)
    suite = unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'), 'test_lp_sp_pricing*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.skipped or result.testsRun != 99:
        raise RuntimeError('incomplete final regression suite')
    for path in (ROOT/'tools').glob('lp_sp_pricing_scale*.py'):
        compile(path.read_text(), str(path), 'exec')
    docs = subprocess.run([sys.executable, '-B', str(ROOT/'tools/build_docs.py')], cwd=ROOT,
                          text=True, capture_output=True, check=True)
    print(docs.stdout, end='', flush=True)
    match = re.search(r'documentation built: (\d+) pages', docs.stdout)
    if not match:
        raise RuntimeError('documentation build receipt missing')
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    put(BASE/identity/'verification.json', dict(status='passed', tests=result.testsRun,
        documentation_pages=int(match[1]), result=binding(BASE/identity/'result.json'),
        outputs=[binding(ROOT/'docs/benchmarks'/name) for name in
                 ['lp-sp-pricing-scale.md', 'lp-sp-pricing-scale-results.json', 'lp-sp-pricing-scale-comparison.csv',
                  'lp-sp-pricing-scale-reconstruction.csv']]))


def settle(identity, reservation):
    validate(); validate_long(); validate_reconstruction(); approval = allocation()
    verification = BASE/identity/'verification.json'
    bindings(read(verification)); summary = resource_summary()
    if summary['pending_at_snapshot']:
        raise RuntimeError('pending reservation')
    receipt = BASE/'resources'/(reservation+'.settlement.json')
    if read(receipt)['status'] != 'passed':
        raise RuntimeError('final verification supervision failed')
    cpu, gpu = accounting(BASE), accounting(BASE, True)
    if any(cpu[p] > CPU[p]*NS or gpu[p] > GPU[p]*NS for p in CPU):
        raise RuntimeError('phase cap exceeded')
    owned = set()
    for pattern in ('*.resource.json', '*.journal.json'):
        for path in (BASE/'resources').glob(pattern):
            owned.update(identities(read(path)))
    if any(still_same_process(*item) for item in owned):
        raise RuntimeError('owned process remains')
    now = dt.datetime.now(dt.timezone.utc)
    started = dt.datetime.fromisoformat(approval['wall_deadline_utc'])-dt.timedelta(hours=2)
    d = dict(status='larger_scale_comparison_settled', verification=binding(verification),
        reporting_settlement=binding(receipt), resources=summary, cpu_phase_ns=cpu, gpu_phase_ns=gpu,
        owned_identities=len(owned), live_owned_identities=[], active_reservations=[],
        tests=read(verification)['tests'], documentation_pages=read(verification)['documentation_pages'],
        settled_utc=now.isoformat(), elapsed_from_campaign_start_seconds=(now-started).total_seconds(),
        within_two_hours=now <= dt.datetime.fromisoformat(approval['wall_deadline_utc']),
        wall_deadline_utc=approval['wall_deadline_utc'])
    put(BASE/identity/'settled-checkpoint.json', d)
    target = ROOT/'docs/benchmarks/lp-sp-pricing-scale-checkpoint.json'
    target.write_text(json.dumps(d, indent=2, sort_keys=True)+'\n')
    (ROOT/'book/docs/benchmarks'/target.name).write_bytes(target.read_bytes())
    print(json.dumps(dict(status=d['status'], cpu_seconds=summary['cpu_ns']/NS,
        gpu_seconds=summary['gpu_ns']/NS, elapsed_seconds=d['elapsed_from_campaign_start_seconds'],
        within_two_hours=d['within_two_hours'], owned_identities=len(owned))), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['verify', 'settle'])
    p.add_argument('identity'); p.add_argument('--reservation'); args = p.parse_args()
    verify_all(args.identity) if args.action == 'verify' else settle(args.identity, args.reservation)
