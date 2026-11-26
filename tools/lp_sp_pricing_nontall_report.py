"""Consolidated implementation report with separate acceptance and timing tiers."""
import argparse
from collections import Counter
import csv
import datetime as dt
import json
from pathlib import Path
import re
import statistics as stats
import subprocess
import sys
import time
import unittest
from lp_sp_pricing_budget import ROOT,BASE,NS,binding,put,accounting
from lp_sp_pricing_nontall_budget import CPU,GPU,allocation
from lp_sp_pricing_nontall_experiment import STUDY,SPECS,validate
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_report import resource_summary
from lp_sp_pricing_finish import identities,still_same_process
from lp_billion_arrays import read as read_array
from lp_sp_pricing_nontall_resume import checked as wide_seal,SEAL
from lp_sp_pricing_nontall_tail import checked as tail_admission,SEAL as SECOND_SEAL
from lp_sp_pricing_nontall_supplement import STUDY as SUPPLEMENT,DRIVER as SUPPLEMENT_DRIVER,validate as supplement_validate

OUT=BASE/'nontall-report-v1';DOCS=ROOT/'docs/benchmarks'
MAIN=BASE/'factor-report-v2';EXTENSION=BASE/'factor-range-extension-v1'
LANES=['candidate','copt-gpu-default','copt-auto']
LABELS={'candidate':'Candidate','copt-gpu-default':'COPT GPU','copt-auto':'COPT CPU auto'}
FAMILIES={'dense-wide-1m':'Dense wide','sparse-wide-1m':'Sparse wide','mixed-square-1m':'Mixed-active square',
    'mixed-rectangular-1p5m':'Mixed-active rectangular','dense-square-4m':'Dense square','banded-square-4m':'Banded sparse square',
    'irregular-square-1m':'Irregular sparse square','scaled-square-1m':'Scaled sparse square'}


def assess_row(source,eligible,cohort):
    row=dict(source,timing_eligible=eligible,cohort=cohort);raw=read(row['raw_audit']['path'])
    if bool(raw['accepted'])!=row['raw_strict_accepted']:raise ArithmeticError('raw acceptance changed')
    if raw.get('proofs'):
        first=raw['proofs'][0]
        if first['tolerance']!=1e-9:raise ArithmeticError('raw tolerance changed')
        row.update(raw_primal_feasible=first['feasible'],raw_finite_bound=first['bound'] is not None)
    else:row.update(raw_primal_feasible=False,raw_finite_bound=False)
    response=read(row['response']['path']) if row.get('response') else {}
    row.update(native_optimal=response.get('status')==1 or (response.get('certificate') or {}).get('status')=='optimal',
        geometry=response.get('geometry_diagnostics',[]),phase_ns=response.get('phase_ns',{}),queries=response.get('queries'),
        process_hwm_bytes=response.get('process_hwm_bytes'),vendor_profile=response.get('profile'),
        gpu_auxiliary_batches=sum(len((e.get('gpu') or {}).get('batches',[])) for e in response.get('events',[])))
    if row['accepted']:
        proof=read(row['proof']['path'])
        if not proof['accepted'] or not proof['primal_feasible'] or proof['visited_nonzeros']!=row['nonzeros']:raise ArithmeticError('incomplete original-model proof')
        if proof.get('kind')=='rigorous_implicit_exact_dual':
            if not proof['supported_on_exactly_active_rows'] or not proof['inverse_proof']['accepted'] or proof['correction_infinity_upper']>proof['minimum_selected_dual_base']:raise ArithmeticError('implicit proof margin')
        elif not proof.get('dual_equations') or not proof.get('zero_gap'):raise ArithmeticError('explicit exact proof')
    return row


def collect():
    f=validate();rows=[];receipts=[]
    wide_seal();tail_admission()
    if read(BASE/'nontall-driver-v3/completed.json')['status']!='all_72_slots_disposed_with_failures_retained':raise RuntimeError('incomplete non-tall driver')
    for index in range(len(SPECS)):
        for kind in ('gpu','cpu'):
            receipt=BASE/'resources'/f'nontall-{kind}-{index}-v1.settlement.json';settlement=read(receipt)
            eligible=settlement['status']=='passed' and settlement['cleanup_empty'] and not settlement['overrun']
            group=read(STUDY/f'{kind}-group-{index}.json')
            if group['status']!='all_slots_disposed':raise RuntimeError('unfinished group')
            receipts.append(binding(receipt))
            rows.extend(assess_row(source,eligible,'primary_non_tall') for source in group['rows'])
    expected={f"{m['name']}-{m['seed']}-{lane}" for m in f['models'] for lane in LANES}
    if len(rows)!=72 or {r['id'] for r in rows}!=expected:raise RuntimeError('roster mismatch')
    return f,rows,receipts


def collect_supplement():
    if not (SUPPLEMENT/'freeze.json').exists():return None,[],[]
    f=supplement_validate();rows=[];receipts=[]
    if read(SUPPLEMENT_DRIVER/'completed.json')['status']!='all_18_fresh_slots_disposed':raise RuntimeError('supplement unfinished')
    for index in range(2):
        for kind in ('gpu','cpu'):
            receipt=BASE/'resources'/f'nontall-supplement-{kind}-{index}-v1.settlement.json';s=read(receipt)
            eligible=s['status']=='passed' and s['cleanup_empty'] and not s['overrun'];group=read(SUPPLEMENT/f'{kind}-group-{index}.json')
            if group['status']!='all_slots_disposed':raise RuntimeError('supplement group unfinished')
            rows.extend(assess_row(r,eligible,'fresh_supplement') for r in group['rows']);receipts.append(binding(receipt))
    expected={f"{m['name']}-{m['seed']}-{lane}" for m in f['models'] for lane in LANES}
    if len(rows)!=18 or {r['id'] for r in rows}!=expected:raise RuntimeError('supplement roster mismatch')
    return f,rows,receipts


def passing(row,tier='exact'):
    return row['timing_eligible'] and row['timely'] and row['accepted' if tier=='exact' else 'raw_strict_accepted']


def comparison(rows,models,tier):
    result=[];key='complete_ns' if tier=='exact' else 'raw_complete_ns'
    for model in models:
        selected={r['lane']:r for r in rows if r['family']==model['name'] and r['seed']==model['seed']}
        for lane in LANES[1:]:
            a,b=selected['candidate'],selected[lane];eligible=passing(a,tier) and passing(b,tier)
            result.append(dict(family=model['name'],seed=model['seed'],control=lane,tier=tier,eligible=eligible,
                candidate_seconds=a[key]/NS,control_seconds=b[key]/NS,control_over_candidate=b[key]/a[key] if eligible else None))
    return result


def median_range(rows,tier='exact'):
    key='complete_ns' if tier=='exact' else 'raw_complete_ns';values=[r[key]/NS for r in rows if passing(r,tier)]
    return '—' if not values else f'{stats.median(values):.3f} [{min(values):.3f}, {max(values):.3f}]'


def elapsed_all(rows,key):
    values=[r[key]/NS for r in rows if r.get(key) is not None]
    return '—' if not values else f'{stats.median(values):.3f}'


def observed_range(rows):
    values=[r['raw_complete_ns']/NS for r in rows if r['timing_eligible']]
    return '—' if not values else f'{stats.median(values):.3f} [{min(values):.3f}, {max(values):.3f}]'


def input_integrity(models):
    start=time.perf_counter_ns();seen=set();size=0
    for model in models:
        raw=read(model['model']['path'])
        for descriptor in raw['arrays'].values():
            key=json.dumps(descriptor,sort_keys=True)
            if key in seen:continue
            array=read_array(BASE,descriptor);size+=array.nbytes;seen.add(key);del array
    return dict(status='all_new_original_array_hashes_verified',unique_array_descriptors=len(seen),decoded_bytes=size,
        elapsed_ns=time.perf_counter_ns()-start,scope='Read original arrays through the unchanged hash-checking decoder; no solve or certificate recomputation. Reporting overhead excluded from performance times.')


def memory_observations():
    result=[]
    for index,spec in enumerate(SPECS):
        for kind in ('gpu','cpu'):
            receipt=read(BASE/'resources'/f'nontall-{kind}-{index}-v1.settlement.json')
            if receipt['status']!='passed':continue
            resource=read(receipt['resource']['path']);record=dict(family=spec['name'],kind=kind,
                resource=receipt['resource'],sampled_aggregate_host_bytes=resource['result']['peak_rss_bytes'])
            if kind=='gpu':
                path=Path(receipt['resource']['path']+'.capacity.jsonl');peak=0;device=0
                for line in path.read_text().splitlines():
                    sample=json.loads(line);gpu=sample['gpu'];owned={str(p) for p in sample['owned_physical_pids']}
                    peak=max(peak,sum(v for p,v in gpu['processes'].items() if p in owned));device=max(device,gpu['used'])
                record.update(capacity=binding(path),sampled_owned_gpu_bytes=peak,sampled_device_used_bytes=device)
            result.append(record)
    return result


def write_report(result,f,prior,extension):
    rows=result['rows'];old=prior['rows'];fresh=[r for r in old if r['cohort']=='optimized_holdout'];candidate=[r for r in rows if r['lane']=='candidate']
    accepted=sum(passing(r) for r in candidate);ep=sum(p['eligible'] for p in result['exact_pairs']);rp=sum(p['eligible'] for p in result['raw_pairs'])
    square_names={s['name'] for s in SPECS if s['m']==s['n'] and not s['mixed']}
    square=[r for r in candidate if r['family'] in square_names];other=[r for r in candidate if r['family'] not in square_names]
    lines=['# Pricing LP implementation and performance across matrix shapes','',
        'Date: November 26, 2026. This report describes the practical certified solver, its relationship to the proposed pricing algorithm, and preparation-inclusive comparisons with COPT 8.0.6. It combines the completed tall study with a fresh non-tall study. The practical implementation is a hybrid of numerical proposals and independent exact acceptance; it does not establish a strongly polynomial implementation.','',
        f'The new primary study covers **24 models and 72 solver slots across eight families**, with three fresh seeds per family. Seven families are square or wide; the eighth is a 1.5:1 rectangular boundary control below the optimized tall dispatch threshold. The candidate produces {accepted}/24 timely exact certificates; {ep}/48 candidate–COPT pairs qualify for exact certified-time comparison and {rp}/48 qualify under the separate raw checker. The retained tall study contributes 108 additional solver slots on 30 models. These cohorts are reported separately because their vendor scaling and postprocessing policies differ.','',
        f'The new results show a substantial dependence on problem structure: the candidate certifies {sum(passing(r) for r in square)}/{len(square)} all-active square inputs, versus {sum(passing(r) for r in other)}/{len(other)} wide or mixed-active inputs. COPT native numerical completions are reported even when the common exact reconstruction fails. These distinctions matter more than an overall average across successful runs.','',
        'The strongest tall result remains the 16M-nonzero family: the optimized candidate median is 16.401 seconds versus 17.451 seconds for the matched COPT GPU control, including preparation and proof. Scaled tall inputs favor COPT. Favorable all-active square cases can finish through CPU factorization without invoking GPU searches; they are evidence for the hybrid solver, not for GPU kernel superiority.','',
        '[All new solver slots](lp-sp-pricing-nontall-comparison.csv), [new structured evidence](lp-sp-pricing-nontall-results.json), [complete tall analysis](lp-sp-pricing-factor.md), and [default-scaling COPT certificate extension](lp-sp-pricing-factor-range.md) retain individual outcomes and phases. A separately labeled fresh-input supplement, when present below, adds coverage without changing the primary denominators.','',
        '## Relationship to the paper','',
        'The [November 24 paper](https://github.com/openai/math/blob/main/preprints/Strongly-polynomial-linear-programming-November-24-2026/paper.pdf) treats exact linear programming through paired nonnegative cones, price queries, compressed calibration, and witness recovery. Our reference modules implement those mathematical components and have component tests, but the full literal parameter regime and recursive execution have not completed within the admitted resources. The practical solver changes calibration, the expert population, iteration limits, and recovery strategy. Its fast paths can prove an optimum before running the pricing search.','',
        '| Component | Implementation | Scope of the evidence |','| --- | --- | --- |',
        '| Reference structure | Exact minors, symbolic logarithmic comparisons, compression and restart invalidation, ellipsoid feasibility, recursive wealth and circuit restrictions | Component and small-model tests; no completed full literal reference execution |',
        '| Practical pricing | Input-height calibration, bounded expert pools, bounded query count and exact restricted-cone recovery | Independently checked practical certificates; no inherited strongly polynomial complexity guarantee |',
        '| Exact CPU market | Integer signed-network flow dual, checked balance and objective equality, lexicographic price recovery | Exact market optimum within native integer-range contracts |',
        '| Auxiliary searches | Shared matrix, synchronized GPU checkpoints, interval screening and exact GMP fallback | Proposal acceleration; uncertain labels never become mathematical decisions |',
        '| Certified presolve | Dense or sparse CPU factorization and eligible tall GPU projections | Original-model optimality certificates; does not exercise all pricing components |','',
        'An accepted practical optimum proves primal feasibility, dual feasibility and zero gap. It does not additionally claim the paper’s strict-complementarity conclusion. Infeasibility and improving-ray verification exist in the earlier implementation; the new large-scale cohorts contain feasible bounded problems only.','',
        '## Solver dispatch and implementation','',
        'The public defaults remain unchanged. The measured opt-in entry point is `tools/lp_sp_pricing_transform_run.py`, with `--representation factor --rho-multiplier 16`. It chooses the tall projection only when m ≥ 2n, n ≤ 4096 and mn ≤ 2^27. Outside that domain it preserves the earlier factor-presolve and native compact-pricing path.','',
        '| Input path | Numerical work | Exact decision and remaining limitation |','| --- | --- | --- |',
        '| Dense square, n ≤ 4096 | CPU LAPACK LU, reused for primal and transposed dual solves | Quantized candidates must pass original-model integer checks; treating every inequality as active can fail |',
        '| Sparse square | CPU sparse LU and transposed solve | Very effective for the banded test matrices; irregular sparsity can create more factor fill |',
        '| Other rectangular shapes | Two bounded LSMR proposals | Least-squares points need not identify the active optimum or a reconstructible exact primal |',
        '| Eligible tall shapes | Resident FP64 GPU projection using a Cholesky factor of AᵀA | Independent implicit dual certificate; normal equations and active-basis reconstruction can be inconclusive |',
        '| Unsuccessful non-tall presolve | Native exact geometry, market and bounded auxiliary searches | GMP reduction and exact witness recovery can consume the solve allowance |','',
        'For the tall proposal, each iteration solves Gx=Aᵀ(b−s−u)+c/ρ with G=AᵀA, then updates the slack projection and scaled multiplier. The factor and state stay resident across batches of 100 updates; only checkpoints cross to the host. A second implemented representation stores AG⁻¹ to replace triangular solves with matrix-vector products, but needs another mn FP64 entries. The evaluated optimized path retains the factor representation. The penalty multiplier was an exploratory choice tested on separate holdouts. Its original tuning reservation failed final supervision, so tuning timings are excluded from performance evidence.','',
        'The exact geometry bottleneck was not simply Python overhead. Native GMP Gauss–Jordan normalization and elimination caused growing rational numerators and denominators, matrix fill and allocation work. A fresh 64-column diagnostic already reached 330-bit rationals and 932,733 counted operations; larger diagnostic reductions hit their limits. Building an implicit null-space representation only after this reduction cannot remove its cost. The tall fast path instead avoids that reduction when its certificate succeeds.','',
        '## GPU concurrency and memory','',
        'The compact auxiliary implementation constructs CPU fallback tableaus lazily. Positive factors describe the paired space; tiles provide products and proof checks without keeping every expanded matrix and transpose. Searches advance synchronously in bounded batches, and active-target compaction retires completed objectives. Two upload slots and separate preparation/checking stages overlap transfers, GPU advancement and host checks. A solve-scoped allocation arena and cached tiles reduce repeated initialization. These mechanisms help the auxiliary stage but cannot eliminate an earlier CPU geometry bottleneck.','',
        'The lean hot path uses FP64 proposals. Earlier FP32 component modes and simulated E2M1 component modes remain research controls; they are not arbitrary precision and are not the basis of the current end-to-end speed claims. The simulated low-precision kernels do not establish packed-FP4 tensor-core throughput. Exact CPU arithmetic and certified enclosures determine acceptance.','',
        'The tall factor path stores roughly mn+n² FP64 matrix entries, plus vectors and library workspaces. The alternative transformed path stores roughly 2mn+n². For m=16000 and n=4000, those matrix terms are approximately 0.596 and 1.073 GiB respectively; they are theoretical representation sizes, not measured device peaks. The implicit certificate still stores an n² floating inverse proposal, bounded by the dispatch limit. It avoids a full rational null-space basis, not every quadratic object.','',
        'This tall GPU implementation densifies A. Forming its Gram matrix costs O(mn²), and an iteration costs O(mn+n²) with the retained factor representation. Its work therefore depends on coefficient positions, not only original nonzeros. The independent proof combines an O(nnz) integer scan with an O(n³) dense inverse-residual product. Very large sparse column dimensions need a different factor/operator strategy; the current dispatch gate prevents implying that these dense costs scale to arbitrary sparse LPs.','',
        '## Certificate rules and timing','',
        'Two acceptance tiers are retained. The original raw checker assesses the returned floating endpoint with its unchanged 1e-9 rules. Its dual bound uses conservative enclosures: for free variables, an uncertain reduced-cost sign can prevent a finite bound even when a native solver reports tiny residuals. A raw refusal is therefore not proof of an incorrect numerical optimum. Native optimal status, primal feasibility, finite-bound availability and exact reconstruction are all recorded separately.','',
        'The second tier reconstructs a certificate using the same policy for every solver in the cohort. An explicit certificate is checked by decoding original binary64 coefficients exactly and scanning the full CSR with arbitrary-precision integers. The implicit tier first establishes an exactly feasible dyadic primal and a nonnegative dyadic dual base y₀ supported on exactly active rows. It selects an active square basis B and defines δ by Bᵀδ=c−Aᵀy₀, with y=y₀+Eδ.','',
        'An untrusted inverse proposal R is accepted only after an independent CPU product and conservative roundoff bounds establish q=‖I−RBᵀ‖∞<1. This gives ‖(Bᵀ)⁻¹‖∞≤‖R‖∞/(1−q). Exact original-model integer residuals then bound ‖δ‖∞. A correction smaller than the selected positive dual margin proves nonnegativity, exact stationarity and zero gap. The enclosure assumes standard IEEE FP64 BLAS arithmetic and rejects non-nearest CPU rounding. It is an implicit mathematical certificate, not a declaration that the raw floating dual was exact.','',
        'Three integer workers scan disjoint CSR blocks while the parent computes the inverse enclosure. Partial stationarity sums are combined as unbounded integers. The prior matched serial controls measured 1.62×, 2.06× and 2.38× checker speedups at 1M, 4M and 16M nonzeros. The new non-tall cohort uses CPU inverse proposals for every lane; its policy also prospectively includes the adaptive-exponent extension for large dual values. Wide primal reconstruction remains unsupported by the implicit dual-only method.','',
        'Raw complete time is model generation/encoding plus the cold solver process and cold raw audit. Exact complete time adds common reconstruction and a cold full independent proof. Solver processes include input validation, CSR-to-CSC conversion where used, library and CUDA startup, preparation, solve, extraction and teardown. COPT imports arrays through its native C API rather than constructing symbolic Python expressions. Thus **COPT preparation is included**; preparation inside COPT_SolveLp remains opaque and is not guessed from its log. Shared model encoding is charged to every lane. Construction-witness validation, idle checks, supervision settlement and extra corruption tests are research overhead, excluded from solver comparisons and included in resource accounting.','',
        'A pair receives a speed ratio only when both original reservations passed, both solver processes returned within the common native allowance, and both endpoints passed the same acceptance tier. A successful proof after a solver deadline does not turn that solve into a timely success. Failed and incomplete slots remain in every denominator.','',
        '## Experimental design','',
        'Hardware: Intel Xeon Platinum 8457C and NVIDIA RTX PRO 6000 Blackwell Server Edition, with four supervised CPU slots. Candidate BLAS uses one thread; COPT uses four CPU threads. The new harness records NumPy '+f['hardware']['numpy']+' and SciPy '+f['hardware']['scipy']+'. COPT is version 8.0.6. These are shared-host measurements without CPU-cache flushing.','',
        'Every new solver gets 60 native seconds and a 90-second process allowance. Reconstruction and proof have separate 90- and 120-second process ceilings. GPU COPT uses PDLP with PDLPTol=1e-9, Presolve=0 and installed default Scaling and Dualize. CPU COPT retains its automatic method and installed presolve/scaling defaults with GPU disabled. The GPU lane is therefore a specified experimental configuration, not an unrestricted claim about COPT defaults. Exact per-cell settings and GPU-startup evidence are retained.','',
        'The candidate pricing fallback also retains its 200-million counted-operation limit, 16384-bit arithmetic limit, 1024-query ceiling, and default exact-storage limits of two million entries and a 4 GiB estimate. Its auxiliary batch width is 32. Reaching an operation or storage limit is reported separately from exhausting the time allowance; these results evaluate the bounded practical configuration. Both vendor lanes set FeasTol and DualTol to 1e-9, MatrixTol=0 and MemLimit=12000; other unmentioned native parameters retain their recorded defaults. Each experimental reservation uses a 32 GiB aggregate host envelope within the existing global resource limits.','',
        'The sparse-wide and mixed-square candidate/GPU groups each wrote all six results, then failed final supervision with coordinator_lost. Each full 2400 CPU / 600 GPU-second charge is retained; cleanup is empty and no overrun is recorded. Fresh read-only seals verify retained records and the absence of recorded owned processes, without regrading supervision or repeating solves. All twelve timings are excluded from performance tables and ratios; raw recorded outcomes remain in the CSV. The preceding triggers are not established. Source inspection identifies a plausible race when cleanup kills an active storage-inventory helper. Untouched groups use a tested, bounded wait for that owned helper to finish naturally before exiting, inside the existing reservation. No signals, synthetic heartbeats, sampling changes or resource exceptions are introduced.','',
        'The candidate and GPU COPT order rotates within each family. CPU controls run in separate CPU-only groups, with the CPU/GPU group order alternating between families. This avoids charging GPU reservation time to CPU-only runs, but does not fully randomize all three solvers together. Each seed has one cold timing, so the medians and ranges below describe these samples rather than confidence intervals.','',
        '| New family | Rows × columns | Nonzeros | Structure |','| --- | ---: | ---: | --- |']
    for spec in SPECS:
        description=('20% inactive inequalities' if spec['mixed'] else 'all inequalities active at the planted optimum')
        if spec['layout']=='random':description+='; independent random column subsets'
        elif spec['degree']<spec['n']:description+='; shifted contiguous row neighborhoods'
        if spec['scaled']:description+='; row factors 2⁻⁴ through 2⁴'
        lines.append(f'| {FAMILIES[spec["name"]]} | {spec["m"]:,} × {spec["n"]:,} | {spec["m"]*spec["degree"]:,} | {description} |')
    lines+=['','Seeds are 125101, 125123 and 125149. All inputs are synthetic signed dyadics with planted feasible primal and nonnegative complementary dual vectors; generation checks those witnesses, but the solvers receive only A, b and c. This gives known finite optima and reproducibility while favoring short-dyadic reconstruction and, in all-active square cases, two direct linear solves. The objective is bounded; the feasible region need not be bounded. Banded sparsity is favorable to sparse factorization; the irregular family tests a different fill pattern. These cases do not represent a real-world application distribution. “Million scale” refers to original nonzeros, not millions of variables.','',
        '## New non tall outcomes','',
        'Counts below require timely completion and passed supervision. “Native optimal” is the solver status before independent certification; it is not a speedup eligibility rule.','',
        '| Family | Candidate exact / 3 | COPT GPU native optimal / exact | COPT CPU native optimal / exact | Excluded timings candidate / GPU / CPU |','| --- | ---: | ---: | ---: | ---: |']
    for spec in SPECS:
        selected={lane:[r for r in rows if r['family']==spec['name'] and r['lane']==lane] for lane in LANES}
        native=lambda lane:sum(r['native_optimal'] and r['timely'] and r['timing_eligible'] for r in selected[lane])
        exact=lambda lane:sum(passing(r) for r in selected[lane])
        excluded=' / '.join(str(sum(not r['timing_eligible'] for r in selected[lane])) for lane in LANES)
        lines.append(f'| {FAMILIES[spec["name"]]} | {exact("candidate")}/3 | {native(LANES[1])}/3 / {exact(LANES[1])}/3 | {native(LANES[2])}/3 / {exact(LANES[2])}/3 | {excluded} |')
    lines+=['','The next table shows the observed raw pipeline duration for **all attempts**, including deadlines and uncertified numerical endpoints. It includes generation/encoding, the cold solver process and raw checking, but excludes reconstruction. In combination with the status counts, this exposes fast numerical COPT completions even where exact recovery fails. These values are not certified solution times and do not support certified speedup ratios.','',
        '| Family | Candidate observed seconds | COPT GPU observed seconds | COPT CPU auto observed seconds |','| --- | ---: | ---: | ---: |']
    for spec in SPECS:lines.append('| '+FAMILIES[spec['name']]+' | '+' | '.join(observed_range([r for r in rows if r['family']==spec['name'] and r['lane']==lane]) for lane in LANES)+' |')
    lines+=['','Exact complete seconds are median [minimum, maximum] over timely accepted endpoints only. Read them with the success counts above; a missing value means no qualifying endpoint, not zero runtime. Ratios below use matched accepted pairs rather than dividing unrelated medians.','',
        '| Family | Candidate | COPT GPU | COPT CPU auto |','| --- | ---: | ---: | ---: |']
    for spec in SPECS:lines.append('| '+FAMILIES[spec['name']]+' | '+' | '.join(median_range([r for r in rows if r['family']==spec['name'] and r['lane']==lane]) for lane in LANES)+' |')
    lines+=['','| Family | Exact GPU pairs / 3 and median COPT / candidate | Exact CPU pairs / 3 and median COPT / candidate |','| --- | ---: | ---: |']
    for spec in SPECS:
        cells=[]
        for lane in LANES[1:]:
            ps=[p for p in result['exact_pairs'] if p['family']==spec['name'] and p['control']==lane and p['eligible']]
            cells.append(f'{len(ps)}/3; '+('—' if not ps else f'{stats.median(p["control_over_candidate"] for p in ps):.3f}×'))
        lines.append('| '+FAMILIES[spec['name']]+' | '+' | '.join(cells)+' |')
    lines+=['','The raw acceptance tier has different eligibility and excludes postprocessing time:','',
        '| Family | Candidate raw accepted / 3 and seconds | COPT GPU raw accepted / 3 and seconds | COPT CPU raw accepted / 3 and seconds |','| --- | ---: | ---: | ---: |']
    for spec in SPECS:
        cells=[]
        for lane in LANES:
            selected=[r for r in rows if r['family']==spec['name'] and r['lane']==lane]
            cells.append(f'{sum(passing(r,"raw") for r in selected)}/3; {median_range(selected,"raw")}')
        lines.append('| '+FAMILIES[spec['name']]+' | '+' | '.join(cells)+' |')
    if result['supplemental_rows']:
        extra=result['supplemental_rows']
        lines+=['','## Fresh timing coverage after supervision failures','',
            'A separately frozen supplement uses three entirely new seeds, 125701, 125723 and 125749, for sparse-wide and mixed-active square inputs. It adds six models and eighteen solver slots using the unchanged algorithms, vendor configurations and certificate policy. It was specified after the original groups lost timing eligibility; no earlier LP is repeated and no failure or excluded timing is replaced. These medians are a separate cohort.','',
            '| Family and lane | Native optima / 3 | Raw accepted / 3 | Exact accepted / 3 | Excluded timings | Observed raw pipeline seconds | Exact complete seconds |','| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
        for family in ('sparse-wide-1m','mixed-square-1m'):
            for lane in LANES:
                selected=[r for r in extra if r['family']==family and r['lane']==lane]
                native=sum(r['timing_eligible'] and r['timely'] and r['native_optimal'] for r in selected)
                lines.append(f'| {FAMILIES[family]} / {LABELS[lane]} | {native}/3 | {sum(passing(r,"raw") for r in selected)}/3 | {sum(passing(r) for r in selected)}/3 | {sum(not r["timing_eligible"] for r in selected)} | {observed_range(selected)} | {median_range(selected)} |')
        lines+=['','Observed raw-pipeline durations include unsuccessful attempts. Only the separate accepted columns qualify a duration as certified; native optimality alone does not. The new data therefore restore measurable coverage without manufacturing exact-certificate speedup pairs.','']
        lines+=['The first supplement setup reservation stopped before model generation because the envelope check encountered its own active reservation. Its full 480 CPU-second charge remains. The corrected setup records the full budget envelope before reserving generation; every subsequent job still performs the original reservation checks. No scientific attempt was repeated.','']
    lines+=['','## Failure modes and measured costs','',
        'The following candidate phase medians include all three attempts per family, including deadlines. They explain consumed time and are not certified speedup measurements. Geometry event durations can be nested within solver phases and must not be added to those phases. Missing counters on a failed native reduction are not zero work.','',
        '| Family | Solver process s | Reconstruction s | Independent proof s | Presolve successes / 3 | Median recorded geometry s | Median pricing queries |','| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for spec in SPECS:
        selected=[r for r in candidate if r['family']==spec['name'] and r['timing_eligible']]
        if not selected:
            lines.append(f'| {FAMILIES[spec["name"]]} | — | — | — | — | — | — |');continue
        geometry=stats.median(sum(g.get('complete_ns',0) for g in r['geometry'])/NS for r in selected)
        queries=[r['queries'] for r in selected if r['queries'] is not None]
        lines.append(f'| {FAMILIES[spec["name"]]} | {elapsed_all(selected,"process_ns")} | {elapsed_all(selected,"postprocess_ns")} | {elapsed_all(selected,"proof_ns")} | {sum(r["route"]=="exact_certified_factor_presolve" for r in selected)}/3 | {geometry:.3f} | {stats.median(queries) if queries else "—"} |')
    wide=[r for r in candidate if r['family']=='dense-wide-1m' and r['timing_eligible']]
    if wide:
        market=stats.median(r['phase_ns'].get('market',0)/NS for r in wide);aux=stats.median(r['phase_ns'].get('auxiliary_labels',0)/NS for r in wide)
        geom=stats.median(sum(g.get('complete_ns',0) for g in r['geometry'])/NS for r in wide)
        lines+=['',f'On these three dense-wide attempts, median recorded geometry time is {geom:.3f} seconds, versus {market:.3f} seconds for the exact market stage and {aux:.3f} seconds for auxiliary labels. The auxiliary stage includes its associated checking, not only kernel-active GPU time. These are failed-solve diagnostics: reducing auxiliary time alone cannot remove the dominant geometry cost.','']
    lines+=['','COPT’s journal separates the adapter from its opaque solve call. The adapter column sums recorded input validation, installation/library setup, conversion, import, extraction and teardown outside SolveLp. Python process startup, common encoding and audits are additional costs already included in the complete totals. GPU preparation inside SolveLp cannot be separated by this interface. These phase medians include unsuccessful returned responses.','',
        '| Family | GPU adapter s | GPU SolveLp s | CPU adapter s | CPU SolveLp s |','| --- | ---: | ---: | ---: | ---: |']
    for spec in SPECS:
        cells=[]
        for lane in LANES[1:]:
            profiles=[r['vendor_profile']['exclusive_ns'] for r in rows if r['family']==spec['name'] and r['lane']==lane and r['timing_eligible'] and r.get('vendor_profile')]
            cells.extend(['—','—'] if not profiles else [f'{stats.median(sum(v for k,v in p.items() if k!="solve_call_opaque") for p in profiles)/NS:.3f}',f'{stats.median(p["solve_call_opaque"] for p in profiles)/NS:.3f}'])
        lines.append('| '+FAMILIES[spec['name']]+' | '+' | '.join(cells)+' |')
    lines+=['','Memory observations cover each three-seed group, including its cold subprocesses and proofs. GPU groups contain both the candidate and GPU COPT; their peaks cannot be attributed to one lane. Host values are sampled aggregate RSS, and GPU values sum listed owned-process allocations. They are observations rather than exact peaks or hard memory enclosures. Failed groups are excluded here.','',
        '| Family | Candidate/GPU group host GiB | Same group owned GPU GiB | CPU control group host GiB |','| --- | ---: | ---: | ---: |']
    for spec in SPECS:
        observed={r['kind']:r for r in result['memory_observations'] if r['family']==spec['name']}
        def memory(kind,key):return '—' if kind not in observed else f'{observed[kind][key]/2**30:.3f}'
        lines.append('| '+FAMILIES[spec['name']]+' | '+' | '.join([memory('gpu','sampled_aggregate_host_bytes'),memory('gpu','sampled_owned_gpu_bytes'),memory('cpu','sampled_aggregate_host_bytes')])+' |')
    lines+=['','Every unsuccessful exact slot is retained by lane and observed disposition:','',
        '| Lane | Disposition | Count |','| --- | --- | ---: |']
    for lane in LANES:
        failures=Counter((str(r['status']),r.get('reason') or r.get('reconstruction_reason') or 'no accepted exact certificate') for r in rows if r['lane']==lane and not passing(r))
        for (status,reason),count in sorted(failures.items()):
            label={'1':'native optimum','8':'time limit','10':'interrupted'}.get(status,status)
            lines.append(f'| {LABELS[lane]} | {label}: {reason} | {count} |')
    lines+=['','COPT numerical completions that lack an exact reconstruction remain informative about optimization throughput but do not supply exact certified-time ratios. In particular, a wide problem may have many optimal primal points; a solver’s returned point need not be the short-dyadic point used only during generation. Our implicit correction changes the dual, so it cannot repair an arbitrary wide primal. Mixed-active square cases also expose the all-equalities assumption of the old presolve. Neither limitation should be hidden by selecting only easy all-active square inputs.','',
        '## Retained tall comparison','',
        'These are the earlier independent holdouts using the optimized tall projection and their own common postprocessor. Their primary GPU COPT control disables Scaling; do not pool its times with the new default-scaling non-tall GPU lane. All entries include preparation and exact proof.','',
        '| Family | Candidate median [range] s | COPT GPU median [range] s | Eligible pairs / 3 | Median COPT / candidate |','| --- | ---: | ---: | ---: | ---: |']
    for family in ('mixed-tall-1m','mixed-tall-4m','mixed-tall-16m','mixed-scaled-tall-4m','dense-4m'):
        qs=[q for q in prior['optimized_pairs'] if q['family']==family and q['control']=='copt-gpu-1e9' and q['eligible']]
        ratio='—' if not qs else f'{stats.median(q["control_over_candidate"] for q in qs):.3f}×'
        lines.append(f'| {family} | {median_range([r for r in fresh if r["family"]==family and r["lane"]=="optimized"])} | {median_range([r for r in fresh if r["family"]==family and r["lane"]=="copt-gpu-1e9"])} | {len(qs)}/3 | {ratio} |')
    lines+=['','The primary tall cohort has 16/30 eligible candidate–COPT pairs, and the optimized cohort has 14/15 against its primary GPU control. Three additional default-scaling COPT endpoints on scaled tall inputs receive exact certificates after a separately disclosed adaptive-range extension. Their complete composed costs are 8.916, 9.408 and 7.755 seconds versus candidate costs 11.310, 10.297 and 10.292 seconds. Those totals include the original failed reconstruction and every later reconstruction/proof phase; they were not measured as a new continuous solver run.','',
        'All six earlier square old/new controls had identical exact certificates, with median new/old native and complete ratios 1.005 and 1.000. The new non-tall cohort extends shape coverage without changing the candidate’s numerical sources. It tests the limits of that unchanged dispatch rather than tuning to the new seeds.','',
        '## Earlier large square capacity coverage','',
        'The [earlier 39-slot scale study](lp-sp-pricing-scale.md) separately includes 4000×4000 dense matrices with 16M nonzeros and 40000×40000 sparse scaled matrices with 10M nonzeros. Its first-seed candidate complete independently audited times are 17.915 and 22.877 seconds respectively. These are CPU factor-presolve results under a 120-second native allowance. Its GPU COPT control uses the older scale-off PDLPTol=1e-12 configuration, and neither comparator supplies an eligible exact pair for those two cases.','',
        'That older study also has a separately frozen 300-second cohort. One whole second-seed candidate/GPU group failed resource finalization after writing results; those timings remain excluded. The old cohort’s sole eligible reconstructed pair, dense 4M against automatic CPU COPT, remains a separate historical observation. These older sizes extend capacity coverage but are not pooled with the new settings or converted into speed ratios against failed controls.','',
        '## Validation and reproducibility','',
        'The preceding tall implementation passes all four CUDA sanitizers after correcting the uninitialized unused Cholesky triangle. Its original failed sanitizer and all failed tuning/admission reservations remain charged. Independent exact-Fraction tests cover inverse bounds and corrections; serial/parallel checks agree on exact residuals. The prior tall study includes 120 deliberate negative-dual/zero-inverse challenges across its original and range-extension certificates. The fresh non-tall generator adds three tests covering exact construction across shapes, deterministic generation and roster coverage. Two exit-coordination tests check exact helper selection and original coordinator identity; a separately supervised smoke check exercises the bounded wait. The final full regression suite contains 117 tests.','',
        'The local evidence retains immutable model hashes, generator seeds, original witnesses kept outside solver inputs, solver commands, settings, logs, every returned response, raw audits, exact proofs, source snapshots and resource receipts. The new report verifies every referenced binding and every accepted proof’s full original nonzero count, and hash-checks every new original input array again. This additional integrity scan is reporting overhead, not added to solver performance. A freeze is a one-time experiment record, not a reusable command: reproducing the numerical experiment requires new identities and current admission, while the report can be regenerated from retained data under a fresh reporting identity.','',
        'Relevant entry points are `tools/lp_sp_pricing_nontall_experiment.py` for the frozen follow-up, `tools/lp_sp_pricing_transform_run.py` for the candidate, `tools/lp_sp_pricing_factor_parallel_proof.py` for implicit verification, and `tools/lp_sp_pricing_scale_verify.py` for explicit verification. `tools/lp_sp_pricing_nontall_report.py` assembles this report and the CSV. The [final checkpoint](lp-sp-pricing-nontall-checkpoint.json) records settled accounting and the absence of active owned work.','',
        'Cumulative ceilings remain 240000 CPU and 30000 GPU seconds, including all preceding SP-LP work and failed full charges. The new request authorizes a fresh two-hour follow-up envelope; the previous two-hour result and deadline are unchanged. Unused GPU admission/development allowance transfers prospectively to confirmation. Four CPU slots, host/device limits, physical headroom, fresh idle observations and exact process ownership remain enforced.','',
        '## Interpretation and next priorities','',
        'The results support targeted fast paths, not general LP dominance. Three seeds provide useful regression coverage but are too few for a broad statistical claim; all large cases are synthetic, feasible and bounded. The normal-equation projection, dyadic primal reconstruction, square active-basis requirement and explicit inverse-proposal dimension cap remain practical restrictions. The current record does not demonstrate robust infeasible/unbounded performance at this scale or a completed literal strongly polynomial solver.','',
        'The next algorithmic priorities are general exact primal-and-dual recovery for wide and mixed-active inputs, and evaluating the factorized projection below the current 2:1 aspect-ratio threshold on fresh holdouts. Avoiding native rational elimination during later pricing reductions is also necessary. These changes would address capability gaps that faster auxiliary kernels alone cannot repair. Irregular sparse factors and automatic vendor configurations should remain controls, followed by external application LPs, stronger scaling/degeneracy stress, and additional independent repetitions before changing public defaults.','']
    path=DOCS/'lp-sp-pricing-comprehensive.md';path.write_text('\n'.join(lines));return path


def verify_all():
    f,rows,receipts=collect();sf,extra,sreceipts=collect_supplement();OUT.mkdir(exist_ok=False)
    prior=read(MAIN/'result.json');extension=read(EXTENSION/'result.json')
    for path in (MAIN/'verification.json',MAIN/'settled-checkpoint.json',EXTENSION/'verification.json',EXTENSION/'settled-checkpoint.json'):bindings(read(path))
    exits=sorted((BASE/'nontall-driver-v3').glob('*.exit.json'))+sorted(SUPPLEMENT_DRIVER.glob('*.exit.json'))
    for path in exits:
        record=read(path)
        if record['status']!='owned_inventory_quiescent' or record['signals_sent'] or record['resource_observation_changes'] or record['command_returncode']:raise RuntimeError('exit coordination receipt')
    result=dict(status='complete_non_tall_comparison',freeze=binding(STUDY/'freeze.json'),rows=rows,settlements=receipts,
        exact_pairs=comparison(rows,f['models'],'exact'),raw_pairs=comparison(rows,f['models'],'raw'),
        supplemental_rows=extra,supplemental_freeze=binding(SUPPLEMENT/'freeze.json') if sf else None,supplemental_settlements=sreceipts,
        supplemental_exact_pairs=comparison(extra,sf['models'],'exact') if sf else [],supplemental_raw_pairs=comparison(extra,sf['models'],'raw') if sf else [],
        prior_result=binding(MAIN/'result.json'),range_extension=binding(EXTENSION/'result.json'),
        source=binding(__file__),failed_group_seals=[binding(SEAL/'result.json'),binding(SECOND_SEAL/'result.json')],exit_coordination=[binding(p) for p in exits],
        input_integrity=input_integrity(f['models']+(sf['models'] if sf else [])),memory_observations=memory_observations(),resources=resource_summary(),generated_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    result['checked_bindings']=bindings(result)+bindings(f);put(OUT/'result.json',result)
    target=DOCS/'lp-sp-pricing-nontall-results.json';target.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    columns=['cohort','id','family','seed','lane','rows','columns','nonzeros','status','reason','route','timing_eligible','timely','native_optimal','raw_primal_feasible','raw_finite_bound','raw_strict_accepted','accepted','certificate_kind','native_ns','encoding_ns','process_ns','raw_audit_ns','postprocess_ns','proof_ns','raw_complete_ns','complete_ns','queries','gpu_auxiliary_batches']
    csvpath=DOCS/'lp-sp-pricing-nontall-comparison.csv'
    with csvpath.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader();writer.writerows({k:r.get(k) for k in columns} for r in rows+extra)
    doc=write_report(result,f,prior,extension)
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'),'test_lp_sp_pricing*.py');outcome=unittest.TextTestRunner(verbosity=2).run(suite)
    if not outcome.wasSuccessful() or outcome.testsRun!=117 or outcome.skipped:raise RuntimeError('full regression suite')
    for path in (ROOT/'tools').glob('lp_sp_pricing_nontall*.py'):compile(path.read_text(),str(path),'exec')
    # The final checkpoint is created only after this reservation settles;
    # create a prospective link target without a claim of settled success.
    checkpoint=DOCS/'lp-sp-pricing-nontall-checkpoint.json'
    if not checkpoint.exists():checkpoint.write_text(json.dumps(dict(status='awaiting_final_reporting_settlement',report=binding(doc)),indent=2)+'\n')
    docs=subprocess.run([sys.executable,'-B',str(ROOT/'tools/build_docs.py')],cwd=ROOT,text=True,capture_output=True,check=True);print(docs.stdout,end='',flush=True)
    pages=int(re.search(r'documentation built: (\d+) pages',docs.stdout)[1]);subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    put(OUT/'verification.json',dict(status='passed',tests=outcome.testsRun,documentation_pages=pages,result=binding(OUT/'result.json'),
        outputs=[binding(p) for p in (doc,target,csvpath)],source=binding(__file__)))


def settle(reservation):
    validate();approval=allocation();verification=read(OUT/'verification.json');bindings(verification);summary=resource_summary()
    receipt=BASE/'resources'/(reservation+'.settlement.json')
    if read(receipt)['status']!='passed' or summary['pending_at_snapshot']:raise RuntimeError('report supervision or active reservation')
    cpu,gpu=accounting(BASE),accounting(BASE,True)
    if any(cpu[p]>CPU[p]*NS or gpu[p]>GPU[p]*NS for p in CPU):raise RuntimeError('phase limit')
    owned=set()
    for pattern in ('*.resource.json','*.journal.json'):
        for path in (BASE/'resources').glob(pattern):owned.update(identities(read(path)))
    if any(still_same_process(*item) for item in owned):raise RuntimeError('owned process remains')
    now=dt.datetime.now(dt.timezone.utc);deadline=dt.datetime.fromisoformat(approval['wall_deadline_utc'])
    checkpoint=dict(status='non_tall_comparison_and_full_report_settled',verification=binding(OUT/'verification.json'),reporting_settlement=binding(receipt),
        resources=summary,cpu_phase_ns=cpu,gpu_phase_ns=gpu,active_reservations=[],live_owned_identities=[],owned_identities=len(owned),
        tests=verification['tests'],documentation_pages=verification['documentation_pages'],settled_utc=now.isoformat(),
        elapsed_from_followup_start_seconds=(now-(deadline-dt.timedelta(hours=2))).total_seconds(),within_two_hours=now<=deadline)
    put(OUT/'settled-checkpoint.json',checkpoint);target=DOCS/'lp-sp-pricing-nontall-checkpoint.json';target.write_text(json.dumps(checkpoint,indent=2,sort_keys=True)+'\n')
    (ROOT/'book/docs/benchmarks'/target.name).write_bytes(target.read_bytes())
    print(json.dumps(dict(status=checkpoint['status'],cpu_seconds=summary['cpu_ns']/NS,gpu_seconds=summary['gpu_ns']/NS,within_two_hours=checkpoint['within_two_hours'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','settle']);p.add_argument('--identity',default='nontall-report-v1');p.add_argument('--reservation');a=p.parse_args();OUT=BASE/a.identity
    verify_all() if a.action=='verify' else settle(a.reservation)
