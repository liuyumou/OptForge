"""Preparation-inclusive recovery comparisons, unchanged-path controls and proof evidence."""
import argparse
from collections import Counter
import csv
import datetime as dt
import json
from pathlib import Path
import re
import statistics as st
import subprocess
import sys
import unittest
from lp_sp_pricing_budget import ROOT,BASE,NS,binding,put,accounting
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_report import resource_summary
from lp_sp_pricing_finish import identities,still_same_process
from lp_sp_pricing_nontall_report import input_integrity
from lp_sp_pricing_rectangular_budget import CPU,GPU,allocation
import lp_sp_pricing_recovery_experiment_v2 as primary
import lp_sp_pricing_recovery_parallel_experiment as final
import lp_sp_pricing_recovery_tail as tail
import lp_sp_pricing_rectangular_study_v2 as rect
import lp_sp_pricing_rectangular_tail as rect_tail

OUT=BASE/'recovery-report-v1';DOCS=ROOT/'docs/benchmarks'
LANES=['candidate','copt-gpu-default','copt-auto']
LABELS={'candidate':'Candidate','copt-gpu-default':'COPT GPU','copt-auto':'COPT CPU auto','old':'Previous candidate'}

def assess(source,model,receipt,cohort):
    settlement=read(receipt);eligible=settlement['status']=='passed' and settlement['cleanup_empty'] and not settlement['overrun']
    row=dict(source,timing_eligible=eligible,cohort=cohort,settlement=binding(receipt))
    if (row['rows'],row['columns'],row['nonzeros'])!=(model['m'],model['n'],model['nonzeros']):raise ArithmeticError('model dimensions changed')
    raw=read(row['response']['path']) if row.get('response') else {};audit=read(row['raw_audit']['path'])
    if audit.get('proofs') and audit.get('tolerance')!=1e-9:raise ArithmeticError('raw tolerance changed')
    if audit['accepted']!=row['raw_strict_accepted']:raise ArithmeticError('raw acceptance changed')
    for p in audit.get('proofs',[]):
        if p['tolerance']!=1e-9:raise ArithmeticError('raw tolerance changed')
    row.update(native_optimal=raw.get('status')==1 or (raw.get('certificate') or {}).get('status')=='optimal',
        proposal=raw.get('proposal'),prior_presolve=raw.get('prior_presolve'),vendor_profile=raw.get('profile'),queries=raw.get('queries'))
    if row['lane']=='copt-gpu-default' and row['native_optimal'] and row.get('gpu_confirmed') is not True:raise ArithmeticError('COPT GPU startup not confirmed')
    if row['accepted']:
        proof=read(row['proof']['path'])
        if not proof['accepted'] or not proof['primal_feasible'] or proof['visited_nonzeros']!=model['nonzeros'] or proof['model']!=model['model']:raise ArithmeticError('incomplete original-model proof')
        if proof.get('certificate',proof.get('response'))!=row['reconstructed'] or (proof['rows'],proof['columns'])!=(model['m'],model['n']):raise ArithmeticError('proof endpoint or dimensions changed')
        if proof.get('kind')=='rigorous_implicit_exact_primal':
            if not proof['dual_equations'] or not proof['dual_nonnegative'] or not proof['inverse_proof']['accepted'] or not proof['zero_gap']:raise ArithmeticError('implicit primal proof')
        elif proof.get('kind')=='rigorous_implicit_exact_dual':
            if not proof['supported_on_exactly_active_rows'] or not proof['inverse_proof']['accepted'] or proof['correction_infinity_upper']>proof['minimum_selected_dual_base']:raise ArithmeticError('implicit dual proof')
        elif not proof.get('dual_equations') or not proof.get('zero_gap') or not proof.get('published_endpoint_matches'):raise ArithmeticError('explicit exact proof')
    return row

def collect(module,driver,expected,cohort,controls=False):
    f=module.frozen()
    if module is final:
        tail.frozen();done=read(tail.DRIVER/'completed.json')
        if done['status']!='all_45_original_and_9_supplement_slots_disposed_failure_retained':raise RuntimeError('incomplete final tail')
    else:
        done=read(BASE/driver/'completed.json')
        if done['status']!=f'all_{expected}_slots_disposed':raise RuntimeError('incomplete comparison driver')
    rows=[]
    prefix='recovery-parallel' if module is final else 'recovery'
    for index in range(5):
        models=f['models'][3*index:3*index+3]
        for kind in ('gpu','cpu'):
            group=read(module.STUDY/f'{kind}-group-{index}.json')
            if group['status']!='all_slots_disposed':raise RuntimeError('unfinished group')
            for row in group['rows']:
                model=next(m for m in models if m['seed']==row['seed'])
                rows.append(assess(row,model,BASE/'resources'/f'{prefix}-{kind}-{index}-v1.settlement.json',cohort))
    if controls:
        for index in range(2):
            for row in read(module.STUDY/f'control-group-{index}.json')['rows']:
                model=next(m for m in f['controls'] if m['name']==row['family'] and m['seed']==row['seed'])
                rows.append(assess(row,model,BASE/'resources'/f'recovery-control-{index}-v1.settlement.json','unchanged_path_controls'))
    ids={f"{m['name']}-{m['seed']}-{lane}" for m in f['models'] for lane in LANES}
    if controls:ids|={f"{m['name']}-{m['seed']}-{lane}" for m in f['controls'] for lane in ('old','candidate')}
    if len(rows)!=expected or {r['id'] for r in rows}!=ids:raise RuntimeError('roster mismatch')
    return f,rows

def supplement():
    f=tail.frozen();rows=[]
    for kind in ('gpu','cpu'):
        group=read(tail.STUDY/f'{kind}-group.json')
        if group['status']!='all_slots_disposed':raise RuntimeError('incomplete supplement')
        for row in group['rows']:
            model=next(m for m in f['models'] if m['seed']==row['seed'])
            rows.append(assess(row,model,BASE/'resources'/f'recovery-mixed-supplement-{kind}-v1.settlement.json','mixed_square_supplement'))
    expected={f"{m['name']}-{m['seed']}-{lane}" for m in f['models'] for lane in LANES}
    if len(rows)!=9 or {r['id'] for r in rows}!=expected:raise RuntimeError('supplement roster')
    return f,rows

def rectangular():
    f=rect.frozen();rect_tail.checked();rows=[]
    if read(rect_tail.OUT/'completed.json')['status']!='all_16_slots_disposed_original_driver_collision_retained':raise RuntimeError('rectangular refinement unfinished')
    for kind in ('gpu','cpu','control'):
        group=read(rect.OUT/f'{kind}-group.json')
        if group['status']!='all_slots_disposed':raise RuntimeError('rectangular group incomplete')
        for row in group['rows']:
            model=next(m for m in f['models']+f['controls'] if m['seed']==row['seed'] and m['name']==row['family'])
            rows.append(assess(row,model,BASE/'resources'/('rectangular-gpu-v2.settlement.json' if kind=='gpu' else f'rectangular-holdout-{kind}-v1.settlement.json'),'rectangular_controls' if kind=='control' else 'rectangular_refinement'))
    expected={f"{m['name']}-{m['seed']}-{lane}" for m in f['models'] for lane in ['candidate-before']+LANES}
    expected|={f"{m['name']}-{m['seed']}-{lane}" for m in f['controls'] for lane in ('candidate-before','candidate')}
    if len(rows)!=16 or {r['id'] for r in rows}!=expected:raise RuntimeError('rectangular roster')
    regression=controls([dict(r,lane='old' if r['lane']=='candidate-before' else r['lane']) for r in rows if r['cohort']=='rectangular_controls'],f['controls'])
    if not regression['passed']:raise RuntimeError('rectangular unchanged-path regression gate')
    comparison=[]
    for m in f['models']:
        selected={r['lane']:r for r in rows if r['seed']==m['seed']};a,b=selected['candidate-before'],selected['candidate'];eligible=accepted(a) and accepted(b)
        comparison.append(dict(family=m['name'],seed=m['seed'],eligible=eligible,before_seconds=a['complete_ns']/NS,after_seconds=b['complete_ns']/NS,before_over_after=a['complete_ns']/b['complete_ns'] if eligible else None))
    return f,rows,regression,comparison

def accepted(row,tier='exact'):return row['timing_eligible'] and row['timely'] and row['accepted' if tier=='exact' else 'raw_strict_accepted']

def medrange(rows,key='complete_ns',tier='exact'):
    values=[r[key]/NS for r in rows if accepted(r,tier)]
    return '—' if not values else f'{st.median(values):.3f} [{min(values):.3f}, {max(values):.3f}]'

def pairs(rows,models):
    result=[]
    for m in models:
        selected={r['lane']:r for r in rows if r['family']==m['name'] and r['seed']==m['seed']};a=selected['candidate']
        for lane in LANES[1:]:
            b=selected[lane];eligible=accepted(a) and accepted(b)
            result.append(dict(family=m['name'],seed=m['seed'],control=lane,eligible=eligible,candidate_seconds=a['complete_ns']/NS,control_seconds=b['complete_ns']/NS,
                control_over_candidate=b['complete_ns']/a['complete_ns'] if eligible else None))
    return result

def controls(rows,models):
    records=[]
    for m in models:
        selected={r['lane']:r for r in rows if r['family']==m['name'] and r['seed']==m['seed']};a,b=selected['old'],selected['candidate']
        ac=read(a['response']['path']).get('certificate');bc=read(b['response']['path']).get('certificate');same=bool(ac) and ac==bc
        records.append(dict(family=m['name'],seed=m['seed'],accepted_both=accepted(a) and accepted(b),identical_explicit_certificate=same,
            new_over_old_complete=b['complete_ns']/a['complete_ns'],new_over_old_native=b['native_ns']/a['native_ns']))
    passed=all(r['accepted_both'] and r['identical_explicit_certificate'] for r in records)
    passed=passed and all(st.median(r['new_over_old_complete'] for r in records if r['family']==family)<=1.10 for family in {r['family'] for r in records})
    return dict(passed=passed,rows=records,criterion='All exact certificates preserved and identical; per-family median complete ratio <=1.10.')

def write_report(result,f,ff):
    initial=[r for r in result['primary_rows'] if r['cohort']=='primary'];latest=result['final_rows'] or initial;ps=result['final_pairs'] or result['primary_pairs']
    count=sum(accepted(r) for r in latest if r['lane']=='candidate');paircount=sum(p['eligible'] for p in ps)
    gpu_family_ratios={spec['name']:st.median(p['control_over_candidate'] for p in ps if p['family']==spec['name'] and p['control']=='copt-gpu-default' and p['eligible'])
        for spec in primary.SPECS if any(p['family']==spec['name'] and p['control']=='copt-gpu-default' and p['eligible'] for p in ps)}
    lines=['# Wide and mixed-active LP recovery: implementation and COPT comparisons','',
        'Date: November 26, 2026. This opt-in update addresses the wide and mixed-active failures in the [preceding report](lp-sp-pricing-comprehensive.md), while retaining the successful square and irregular numerical paths. All certified times below include model encoding, cold preparation, solving, endpoint recovery and independent certification.','',
        f'The primary study contains **57 fresh solver attempts on 21 models**: fifteen focus models against COPT GPU and CPU, plus six paired old/new regression models. '+('A second cohort adds **45 fresh attempts on fifteen further models** using a faster common exact checker. ' if ff else '')+f'The second cohort supplies {count}/15 timely, supervised candidate certificates and {paircount}/30 eligible exact candidate–COPT pairs. A separately frozen mixed-square supplement adds nine attempts on three new models, for 111 attempts on 39 models. A final rectangular refinement adds sixteen attempts on five models: **127 comparison attempts on 44 models** in total, plus the separately reported development experiments. All attempted cells, native statuses, failed certificates and deadlines remain visible.','',
        f'Across the second cohort’s eligible matched exact GPU comparisons, the candidate has the lower median complete cost in {sum(v>1 for v in gpu_family_ratios.values())}/{len(gpu_family_ratios)} families. The per-family tables retain the direction and sample count of every comparison, including cases that favor COPT. The six old/new square and irregular regression models retain identical accepted explicit certificates.','',
        'The practical improvement comes from recognizing a full-row-rank feasibility problem and representing its primal implicitly. It bypasses pricing when an independently checkable optimum is available. It does not speed up the paper’s literal recursive algorithm or establish strongly polynomial complexity. The performance conclusions apply to these synthetic cases and specified configurations.','',
        '## Diagnosis','',
        'Dense-wide previously spent a median 54.285 seconds in recorded exact geometry before its deadline. The numerical primal was generally not a short dyadic vector, so the earlier reconstruction failed even when a factor solve could describe a valid optimum. Building an implicit null-space representation after rational elimination did not remove that earlier elimination cost.','',
        'For the three retained, supervised sparse-wide follow-up inputs, the exact CPU market consumed 7.281, 7.327 and 7.324 seconds and returned `native_market_2`. The native source maps that code to its scan cap. The Python work total near two million is incomplete for this failure: the C++ scan metrics are copied back only on a successful return. The earlier cap was approximately 200 million remaining counted scans, not two million. Geometry/expert construction also consumed about 4.23 seconds. These earlier runs did not certify, so their durations are diagnostics rather than certified speedup denominators.','',
        'Mixed-active square cases exposed a different reconstruction limitation. With nonsingular square A, solving Ax=b makes every inequality active and feasible, even when the generated optimum had inactive inequalities. The resulting x may have non-dyadic rational coordinates. If the corresponding exact dual is nonnegative, this all-active point is optimal; rejecting it solely because x cannot be rounded to a short dyadic representation is unnecessary.','',
        '## Factorized recovery and exact acceptance','',
        'For m ≤ n, select m columns J and define B=A[:,J]. The certificate stores a dyadic primal base x₀, an exact dyadic dual y, the column indices J, and a floating inverse proposal R. It defines the actual primal by','',
        '`x = x₀ + E_J δ`, where `B δ = b − A x₀`.','',
        'An independent CPU enclosure proves ‖I−RB‖∞<1 and hence that B is nonsingular. Therefore the defined x satisfies **every original row equality Ax=b**, without explicitly materializing its rational coordinates or an n×(n−m) null-space basis. The enclosure assumes standard IEEE FP64 BLAS roundoff and rejects non-nearest CPU rounding. A full original-CSR scan with arbitrary-precision integers proves y≥0 and Aᵀy=c. Primal feasibility, dual feasibility and zero gap then follow exactly. The corrected primal can differ from the numerical endpoint; its implicit definition is the certified output. Raw floating-endpoint acceptance remains a separate, unchanged 1e-9 tier.','',
        'The first sparse-wide development bases used structural matching. Two certificates were correctly rejected because the matched numerical basis was ill-conditioned. The final constructor first tries two evenly distributed column selections, checks their inverse enclosures, and then retains structural matching as a checked fallback. The final independent checker recomputes the enclosure. No rank or stability decision is taken from the sparsity pattern alone. The rejected development outcomes and original sources remain retained.','',
        '| Input | Final proposal path | Avoided work / limitation |','| --- | --- | --- |',
        '| Dense-wide | Dense CPU BLAS forms AAᵀ; one Cholesky factor solves the two right-hand sides b and Ac; Aᵀ maps the primal back | No rational geometry or market search on accepted recovery; normal equations can be inconclusive |',
        '| Sparse-wide | Sparse AAᵀ and sparse LU, reused for both right-hand sides | No pricing queries or market scans on accepted recovery; sparse factor fill remains shape-dependent |',
        '| Mixed-active square after old presolve rejects | CPU LU solves primal and transposed dual systems, followed by implicit primal recovery | Removes the short-dyadic-primal requirement; exact dual recovery remains bounded |',
        '| Mixed-active rectangular, n < m < 2n | Existing resident FP64 GPU projection extended to the previously unsupported dispatch interval | Avoids rational elimination; retains the bounded preceding CPU presolve and exact postprocessor |',
        '| Successful square/irregular presolve and existing tall dispatch | Original numerical entry point and original success path | No numerical algorithm change; measured regression controls below |','',
        'A separate CUDA implementation forms the wide row-Gram matrix with cuBLAS, factors it with cuSOLVER and solves both right-hand sides together. It passes CPU/GPU differential checks and memcheck, racecheck, initcheck and synccheck. Cold complete development timings favor CPU recovery at the tested sizes, so the frozen wide configuration uses `--wide-backend cpu`. The GPU option remains available and is measured explicitly; moving an operation to GPU is not treated as an end-to-end improvement by itself. Mixed-active rectangular recovery uses GPU projection.','',
        'The primary and second-cohort entry point is `tools/lp_sp_pricing_recovery_run_fast.py --wide-backend cpu`. Common endpoint recovery is `tools/lp_sp_pricing_recovery_endpoint_balanced.py`. Existing square/irregular successes still use their original exact factor presolve; only a rejected presolve enters new recovery. Public defaults and all retained numerical/resource sources are unchanged. New implementations and admissions are additive.','',
        'The wide dense proposal stores O(mn+m²) floating matrix entries. Its certificate has an m² inverse proposal and O(m+n) vectors/indices, rather than a full rational null-space basis. Sparse proposals retain sparse factors but the current certificate still has a dense m×m inverse proposal. The row dimension is capped at 4096, and the proposal shape at mn≤2^27. These are nonzero-scale experiments, not claims about millions of variables.','',
        '## Backend selection and faster host checking','',
        'The backend rule was fixed before holdouts: choose GPU only if its cold complete development cost improved by at least 10%. Each development comparison used a separate solver process and the same certificate pipeline; these single-pair measurements are configuration choices, not a broad performance claim. The CPU dense comparison uses dense BLAS rather than sparse multiplication.','',
        '| Development family | CPU proposal region s | GPU proposal region s | CPU complete s | GPU complete s | Selected |','| --- | ---: | ---: | ---: | ---: | --- |']
    dev=read(BASE/'recovery-development-v2/result.json')
    for family in ('dense-wide-1m','dense-wide-4m','sparse-wide-1m'):
        rs={r['lane']:r for r in dev['rows'] if r['family']==family}
        lines.append(f'| {family} | {rs["candidate-cpu"]["proposal"]["complete_ns"]/NS:.3f} | {rs["candidate-gpu"]["proposal"]["complete_ns"]/NS:.3f} | {rs["candidate-cpu"]["complete_ns"]/NS:.3f} | {rs["candidate-gpu"]["complete_ns"]/NS:.3f} | {f["backend"][family]} |')
    lines+=['','The proposal region includes conversion and factor setup; its GPU measurement also includes cold CUDA/library initialization, allocations, transfers and teardown. It is not kernel-active time. At these dimensions, the complete GPU region costs more than the efficient CPU region, while both pay the same independent CPU certificate work.','']
    if result.get('parallel_profile'):
        profile=read(result['parallel_profile']['path'])
        lines+=['','The final checker overlaps three disjoint exact integer dual scans with the parent’s CPU inverse enclosure. Integer partial sums are combined exactly. All original matrix entries are still checked. The nonsingular correction definition already guarantees Ax=b, so recomputing A x₀ only to display its residual is unnecessary for acceptance and is omitted in the parallel path. Small checks retain the serial implementation.','',
            'The following cold checker-only measurements recheck retained development certificates; they do not repeat LP solves or replace earlier recorded timings. The final cohort below measures the complete updated pipeline on new models.','',
            '| Certificate | Serial cold check s | Parallel cold check s | Serial / parallel |','| --- | ---: | ---: | ---: |']
        for family in ('dense-wide-1m','dense-wide-4m','sparse-wide-1m'):
            rs={r['lane']:r for r in profile['rows'] if r['family']==family};a,b=rs['serial']['cold_process_ns'],rs['parallel']['cold_process_ns']
            lines.append(f'| {family} | {a/NS:.3f} | {b/NS:.3f} | {a/b:.3f}× |')
    lines+=['','## Experimental protocol','',
        'Hardware is the same Intel Xeon Platinum 8457C and NVIDIA RTX PRO 6000 Blackwell Server Edition used previously. COPT is 8.0.6. Each reservation has four CPU slots and a 32 GiB aggregate sampled host envelope; candidate BLAS uses one thread and COPT uses four. Exact parallel checks use three worker processes plus the parent. GPU ownership, physical headroom, idle observations and memory limits remain enforced.','',
        'Every solver requests a 60-second native allowance and a 90-second process ceiling. Reconstruction and proof have 90- and 120-second process ceilings. COPT GPU uses LpMethod=6, GPUMode=1, Presolve=0, Crossover=0 and PDLPTol=1e-9, with installed default Scaling and Dualize. COPT CPU uses its automatic method with GPUMode=0 and installed default presolve/scaling. Both vendor lanes use FeasTol=DualTol=1e-9, MatrixTol=0, MemLimit=12000 and Threads=4. These are specified experimental configurations, not an unrestricted claim about vendor defaults.','',
        'Complete time is common model generation/encoding plus cold solver process, raw audit, common endpoint recovery and cold independent proof. Solver time includes validation, matrix conversion, native import, library/CUDA setup, preparation, optimization, extraction and teardown. In particular, **COPT preparation is included**, including opaque work inside SolveLp. Construction-witness checks, idle admission and experiment supervision are excluded from solver comparisons and included in resource accounting.','',
        'Native optimal status, raw 1e-9 endpoint acceptance and exact reconstruction are distinct. An exact-time ratio requires both reservations to pass, both native attempts to be timely, and both endpoints to pass the same independent exact policy. A native optimal return without an exact certificate is not counted as a certified solve; a deadline never becomes a timely solve through later reconstruction. All denominators retain unsuccessful and missing slots.','',
        'Primary seeds are 126101, 126123 and 126149; regression seeds are 126201, 126223 and 126249. The final checker cohort uses 126401, 126423 and 126449; the separate mixed-square supplement uses 126901, 126923 and 126949. Candidate/GPU order rotates; CPU controls run in separate groups with alternating CPU/GPU group order. There is one cold timing per seed and no cache flush. Ranges describe these samples and are not confidence intervals.','',
        'Inputs are signed dyadic synthetic LPs with independently checked planted witnesses kept outside solver inputs. Wide inputs have all rows active at the planted optimum; mixed inputs have 20% inactive rows there. Their exact short-dyadic duals favor the bounded reconstruction strategy. “Mixed-active” describes the generated optimum, not a guarantee that every optimum has the same active set.','',
        '| Family | Rows × columns | Original nonzeros |','| --- | ---: | ---: |']
    for spec in primary.SPECS:lines.append(f'| {spec["name"]} | {spec["m"]:,} × {spec["n"]:,} | {spec["m"]*spec["degree"]:,} |')
    for title,rows,pairrows in [('Primary cohort with serial implicit-primal checker',initial,result['primary_pairs'])]+([('Final cohort with parallel implicit-primal checker',result['final_rows'],result['final_pairs'])] if ff else []):
        lines+=['',f'## {title}','','Each cell is accepted count / 3 followed by median [minimum, maximum] complete seconds over accepted, timely endpoints. Read durations with their counts; missing entries are not zero runtime.','',
            '| Family | Candidate | COPT GPU | COPT CPU auto |','| --- | ---: | ---: | ---: |']
        for spec in primary.SPECS:
            cells=[]
            for lane in LANES:
                selected=[r for r in rows if r['family']==spec['name'] and r['lane']==lane];cells.append(f'{sum(accepted(r) for r in selected)}/3; {medrange(selected)}')
            lines.append('| '+spec['name']+' | '+' | '.join(cells)+' |')
        lines+=['','| Family | Eligible GPU pairs / 3; median COPT / candidate | Eligible CPU pairs / 3; median COPT / candidate |','| --- | ---: | ---: |']
        for spec in primary.SPECS:
            cells=[]
            for lane in LANES[1:]:
                selected=[p for p in pairrows if p['family']==spec['name'] and p['control']==lane and p['eligible']]
                cells.append(f'{len(selected)}/3; '+('—' if not selected else f'{st.median(p["control_over_candidate"] for p in selected):.3f}×'))
            lines.append('| '+spec['name']+' | '+' | '.join(cells)+' |')
    lines+=['','## Failed finalization and separate mixed-square supplement','',
        'The final mixed-square GPU group wrote all six numerical results and accepting proofs, then supervision failed during finalization with `coordinator_lost`. All six timings are excluded, and the full 600 CPU / 150 GPU seconds remain charged. Cleanup was empty and no overrun occurred. A separately supervised read-only seal verifies the original sources, completed results and absence of all recorded owned identities; it neither recomputes nor regrades the failed group. The preceding failure trigger is unknown. A bounded exit wait now observes an actual completed owned inventory cycle before returning; an inventory race is a hypothesis, not an established cause.', '',
        'Only the two untouched rectangular groups continued. The following separately frozen new mixed-square seeds provide fresh timing coverage with the same solver, vendor settings and parallel checker. They do not replace the failed slots or repair their timing eligibility.', '',
        '| Supplement family | Candidate | COPT GPU | COPT CPU auto |', '| --- | ---: | ---: | ---: |']
    cells=[]
    for lane in LANES:
        selected=[r for r in result['supplement_rows'] if r['lane']==lane];cells.append(f'{sum(accepted(r) for r in selected)}/3; {medrange(selected)}')
    lines.append('| mixed-square-1m | '+' | '.join(cells)+' |')
    for lane in LANES[1:]:
        selected=[p for p in result['supplement_pairs'] if p['control']==lane and p['eligible']]
        lines+=['',f'{LABELS[lane]} supplement: {len(selected)}/3 eligible pairs; median COPT / candidate '+('unavailable.' if not selected else f'{st.median(p["control_over_candidate"] for p in selected):.3f}×.')]
    lines+=['','## Square and irregular regression controls','',
        'These paired runs use identical new inputs and the old versus new candidate. Their explicit certificates must match exactly. The final parallel checker affects only implicit-primal certificates and is not invoked on these explicit-success paths; the numerical candidate and common postprocessor are identical across the two new focus cohorts.','',
        '| Family | Old complete median [range] s | New complete median [range] s | Median new / old complete | Median new / old native | Identical accepted certificates |','| --- | ---: | ---: | ---: | ---: | ---: |']
    for spec in primary.CONTROLS:
        cs=[r for r in result['controls']['rows'] if r['family']==spec['name']];rs=[r for r in result['primary_rows'] if r['cohort']=='unchanged_path_controls' and r['family']==spec['name']]
        lines.append(f'| {spec["name"]} | {medrange([r for r in rs if r["lane"]=="old"])} | {medrange([r for r in rs if r["lane"]=="candidate"])} | {st.median(r["new_over_old_complete"] for r in cs):.3f}× | {st.median(r["new_over_old_native"] for r in cs):.3f}× | {sum(r["accepted_both"] and r["identical_explicit_certificate"] for r in cs)}/3 |')
    rf=read(result['rectangular_freeze']['path']);rrows=result['rectangular_rows'];rdev=read(result['rectangular_development']['path'])
    lines+=['','## Direct rectangular GPU refinement','',
        'The initial mixed rectangular path spent about 0.67 seconds in an unsuccessful CPU LSMR presolve before GPU projection. A final opt-in dispatcher skips that work only for n<m<2n within the existing dimension limits. Every other shape delegates to the preceding implementation. The CUDA kernel, stopping threshold, exact postprocessor and independent proof are unchanged.', '',
        'The first refinement development wrapper failed after its baseline solve because it tried to recreate the common harness’s existing result file. Its baseline timing is excluded and the full 600 CPU / 150 GPU-second charge remains. The other four planned configurations never started. An additive wrapper writes configuration metadata separately, verifies cleanup and prior sources, and uses a new development seed. A prospective transfer moves 150 unused GPU admission seconds into development within unchanged totals and the original deadline.', '',
        'A prospectively bounded development experiment uses one new input (seed 127021), with the preceding candidate and four direct GPU penalty multipliers. Selection requires a timely exact certificate and at least a 10% complete-cost reduction versus the preceding candidate; all alternatives remain in the table. These development timings select a configuration, not a general performance claim.', '',
        '| Development configuration | Exact accepted | GPU updates | Proposal region s | Complete s |','| --- | ---: | ---: | ---: | ---: |']
    for row in rdev['rows']:
        proposal=row.get('proposal') or {};lines.append(f'| {row["lane"]} | {row["accepted"] and row["timely"]} | {proposal.get("steps", "—")} | {proposal.get("complete_ns",0)/NS:.3f} | {row["complete_ns"]/NS:.3f} |')
    lines+=['',f'The frozen choice is rho multiplier **{rf["selected_multiplier"]}**. The measured final entry point is `tools/lp_sp_pricing_rectangular_run.py --wide-backend cpu --rho-multiplier {rf["selected_multiplier"]}`. This remains opt-in; retained public defaults and earlier studies are unchanged.', '',
        'After the nine GPU-group slots completed successfully, the driver detected that its planned CPU reservation identity was already used by the admission job. It stopped before launching any CPU/control cell. A separately supervised continuation verifies the original completed GPU group and sources, and runs only the two untouched groups under fresh reservation names. The original driver is never rerun.', '',
        'Holdout seeds 127301, 127323 and 127349 compare preceding/new candidates and both COPT lanes. All complete times include the same original encoding, cold preparation, raw audit, common endpoint recovery and independent proof. These new measurements are separate from the preceding rectangular cohorts.', '',
        '| Rectangular holdout lane | Exact accepted / 3 | Complete median [range] s |','| --- | ---: | ---: |']
    for lane in ['candidate-before']+LANES:
        selected=[r for r in rrows if r['cohort']=='rectangular_refinement' and r['lane']==lane]
        lines.append(f'| {"Preceding candidate" if lane=="candidate-before" else LABELS[lane]} | {sum(accepted(r) for r in selected)}/3 | {medrange(selected)} |')
    selected=[p for p in result['rectangular_before_after'] if p['eligible']]
    lines+=['',f'Old/new exact pairs: {len(selected)}/3; median preceding / new '+('unavailable.' if not selected else f'{st.median(p["before_over_after"] for p in selected):.3f}×.')]
    for lane in LANES[1:]:
        selected=[p for p in result['rectangular_pairs'] if p['control']==lane and p['eligible']]
        lines+=['',f'{LABELS[lane]} exact pairs: {len(selected)}/3; median COPT / new '+('unavailable.' if not selected else f'{st.median(p["control_over_candidate"] for p in selected):.3f}×.')]
    lines+=['','Two additional square/irregular controls (seeds 127401 and 127403) check the final dispatcher on new inputs. These are one pair per family, supplementary to the three primary pairs per family; they are not a statistical latency guarantee.','',
        '| Final dispatcher control | New / preceding complete | Identical accepted certificate |','| --- | ---: | ---: |']
    for row in result['rectangular_controls']['rows']:
        lines.append(f'| {row["family"]} | {row["new_over_old_complete"]:.3f}× | {row["accepted_both"] and row["identical_explicit_certificate"]} |')
    lines+=['','Both families pass the prespecified no-lost-certificate, identical-certificate and ≤10% median complete-time regression checks. This supports preservation on the measured cases; it is not a universal latency guarantee. Existing tall and larger sparse-square dispatch remains unchanged by source construction.','',
        '## Second-cohort phase costs and unsuccessful slots','',
        'Phase medians below describe the second cohort and include all supervision-eligible returned attempts, including deadlines; they diagnose cost and are not themselves certified speedup ratios. Independent phase medians need not sum to the median complete cost.','',
        '| Family and lane | Encoding s | Solver process s | Raw audit s | Reconstruction s | Independent proof s |','| --- | ---: | ---: | ---: | ---: | ---: |']
    for spec in primary.SPECS:
        for lane in LANES:
            selected=[r for r in latest if r['family']==spec['name'] and r['lane']==lane and r['timing_eligible']]
            values=['—' if not selected else f'{st.median(r[key] for r in selected)/NS:.3f}' for key in ('encoding_ns','process_ns','raw_audit_ns','postprocess_ns','proof_ns')]
            lines.append('| '+spec['name']+' / '+LABELS[lane]+' | '+' | '.join(values)+' |')
    lines+=['','| Second-cohort lane | Native optima | Raw accepted | Exact accepted | Timings excluded |','| --- | ---: | ---: | ---: | ---: |']
    for lane in LANES:
        selected=[r for r in latest if r['lane']==lane]
        lines.append(f'| {LABELS[lane]} | {sum(r["native_optimal"] and r["timely"] and r["timing_eligible"] for r in selected)}/15 | {sum(accepted(r,"raw") for r in selected)}/15 | {sum(accepted(r) for r in selected)}/15 | {sum(not r["timing_eligible"] for r in selected)} |')
    lines+=['','The candidate labels new factor endpoints as numerical proposals pending the common proof, so its native-optimal count is not an acceptance criterion.','',
        '| Second-cohort lane | Unsuccessful exact disposition | Count |','| --- | --- | ---: |']
    for lane in LANES:
        counts=Counter((str(r['status']),('supervision failed; timing excluded' if not r['timing_eligible'] else r.get('reason') or r.get('reconstruction_reason') or 'no accepted exact certificate')) for r in latest if r['lane']==lane and not accepted(r))
        for (status,reason),number in sorted(counts.items()):
            label={'1':'native optimum','8':'time limit','10':'interrupted'}.get(status,status)
            lines.append(f'| {LABELS[lane]} | {label}: {reason} | {number} |')
    lines+=['','## Validation, limits and reproducibility','',
        'The new proof is tested against independent Fraction Gaussian elimination, including an explicitly non-dyadic primal. Corrupted duals, singular/invalid bases, invalid inverses, noncanonical CSR and nonfinite inputs are rejected. Serial and parallel original-model checks agree on small exact cases, and the large checker profile independently accepts each retained development certificate. The final full regression suite contains 137 tests. The new CUDA kernel has four complete sanitizer passes and CPU/GPU numerical comparisons.','',
        'The report hash-checks every retained reference and all new original input arrays, verifies every accepted proof’s original-model binding and full nonzero count, and checks the old/new explicit certificates. All prior failed reservations and scientific rejections remain retained and charged. The first sparse-wide development certificates were rejected; their results are not regraded by the later balanced-basis success.','',
        'Remaining restrictions matter: recovery requires full row rank and a reconstructible nonnegative exact dyadic dual; normal equations may be ill-conditioned; the dense inverse certificate limits row dimension; and sparse normal factors can fill. The initial mixed rectangular recovery pays for bounded CPU LSMR before GPU projection; the final refinement described above removes it only in that rectangular interval. Both use the earlier implicit-dual proof. The new synthetic inputs do not establish behavior on arbitrary real-world, infeasible, unbounded or strongly degenerate LPs.','',
        'The outcomes establish targeted practical improvements and measured regression preservation. They do not establish general superiority over COPT or a complete strongly polynomial implementation. Historical failed candidate solves are not used as speedup denominators, and cohorts with different seeds/checkers are not pooled into a single speed ratio.','',
        '[All comparison slots](lp-sp-pricing-recovery-comparison.csv), [structured evidence](lp-sp-pricing-recovery-results.json), and the [settled checkpoint](lp-sp-pricing-recovery-checkpoint.json) retain individual settings, costs, proofs and supervision. The unchanged cumulative ceilings are 240000 CPU and 30000 GPU seconds, including all preceding work and full failed charges. The current follow-up uses a fresh two-hour envelope; the checkpoint records actual elapsed time and absence of active owned work.','']
    doc=DOCS/'lp-sp-pricing-recovery.md';doc.write_text('\n'.join(lines));return doc

def verify_all():
    f,rows=collect(primary,'recovery-driver-v2',57,'primary',True);ff=None;extra=[]
    if (final.STUDY/'freeze.json').exists():ff,extra=collect(final,'recovery-parallel-driver-v1',45,'parallel_checker')
    sf,srows=supplement();rf,rrows,rcontrols,rcomparison=rectangular()
    OUT.mkdir(exist_ok=False);regression=controls([r for r in rows if r['cohort']=='unchanged_path_controls'],f['controls'])
    if not regression['passed']:raise RuntimeError('square/irregular regression gate failed')
    profile=BASE/'primal-parallel-cpu-v1/result.json'
    preceding=BASE/'nontall-report-v1/result.json';historical=read(preceding);historical_bindings=bindings(historical)
    development_models=[m for name in ('recovery-development-v1','recovery-development-v2') for m in read(BASE/name/'result.json')['models']]
    development_models+=read(rect.DEV/'result.json')['models']
    development_models.append(dict(model=read(BASE/'rectangular-development-v1/runs/candidate-before/response.json')['model']))
    market_records=[binding(BASE/'nontall-supplement-v1/runs'/f'sparse-wide-1m-{seed}-candidate/response.json') for seed in (125701,125723,125749)]
    result=dict(status='complete_recovery_comparison',primary_freeze=binding(primary.STUDY/'freeze.json'),primary_rows=rows,
        primary_pairs=pairs([r for r in rows if r['cohort']=='primary'],f['models']),controls=regression,
        final_freeze=binding(final.STUDY/'freeze.json') if ff else None,final_rows=extra,final_pairs=pairs(extra,ff['models']) if ff else [],
        rectangular_freeze=binding(rect.OUT/'freeze.json'),rectangular_rows=rrows,rectangular_controls=rcontrols,rectangular_before_after=rcomparison,
        rectangular_pairs=pairs([r for r in rrows if r['cohort']=='rectangular_refinement'],rf['models']),rectangular_development=binding(rect.DEV/'result.json'),
        rectangular_completion=binding(rect_tail.OUT/'completed.json'),rectangular_tail_plan=binding(rect_tail.OUT/'plan.json'),
        supplement_freeze=binding(tail.STUDY/'freeze.json'),supplement_rows=srows,supplement_pairs=pairs(srows,sf['models']),
        failure_seal=binding(tail.SEAL/'result.json'),tail_completion=binding(tail.DRIVER/'completed.json'),tail_plan=binding(tail.DRIVER/'plan.json'),
        stopped_driver=binding(BASE/'recovery-parallel-driver-v1/stopped.json'),
        development=[binding(BASE/name/'result.json') for name in ('recovery-development-v1','recovery-development-v2')],
        parallel_profile=binding(profile) if profile.exists() else None,source=binding(__file__),
        preceding_result=binding(preceding),historical_market_responses=market_records,
        historical_market_sources=[binding(ROOT/'research/lp-sp-pricing/native/market.cpp'),binding(ROOT/'research/lp-sp-pricing/python/sp_pricing/flow_market.py')],
        historical_bindings_checked=historical_bindings,
        input_integrity=input_integrity(f['models']+f['controls']+(ff['models'] if ff else [])+sf['models']+rf['models']+rf['controls']+development_models),resources=resource_summary())
    result['checked_bindings']=bindings(result)+bindings(f)+(bindings(ff) if ff else 0)+bindings(sf)+bindings(rf);put(OUT/'result.json',result)
    target=DOCS/'lp-sp-pricing-recovery-results.json';target.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    csvpath=DOCS/'lp-sp-pricing-recovery-comparison.csv';columns=['cohort','id','family','seed','lane','backend','rows','columns','nonzeros','status','reason','route','timing_eligible','timely','native_optimal','raw_strict_accepted','accepted','certificate_kind','native_ns','encoding_ns','process_ns','raw_audit_ns','postprocess_ns','proof_ns','raw_complete_ns','complete_ns','reconstruction_reason']
    with csvpath.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader();writer.writerows({k:r.get(k) for k in columns} for r in rows+extra+srows+rrows)
    doc=write_report(result,f,ff)
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'),'test_lp_sp_pricing*.py');outcome=unittest.TextTestRunner(verbosity=2).run(suite)
    if not outcome.wasSuccessful() or outcome.testsRun!=137 or outcome.skipped:raise RuntimeError('full regression suite')
    for pattern in ('lp_sp_pricing_recovery*.py','lp_sp_pricing_primal*.py','lp_sp_pricing_rectangular*.py'):
        for path in (ROOT/'tools').glob(pattern):compile(path.read_text(),str(path),'exec')
    checkpoint=DOCS/'lp-sp-pricing-recovery-checkpoint.json'
    if not checkpoint.exists():checkpoint.write_text(json.dumps(dict(status='awaiting_reporting_settlement',report=binding(doc)),indent=2)+'\n')
    docs=subprocess.run([sys.executable,'-B',str(ROOT/'tools/build_docs.py')],cwd=ROOT,text=True,capture_output=True,check=True);print(docs.stdout,end='',flush=True)
    pages=int(re.search(r'documentation built: (\d+) pages',docs.stdout)[1]);subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    put(OUT/'verification.json',dict(status='passed',tests=outcome.testsRun,documentation_pages=pages,result=binding(OUT/'result.json'),outputs=[binding(p) for p in (doc,target,csvpath)],source=binding(__file__)))

def settle(reservation):
    rect_tail.checked();rect.frozen();final.frozen();tail.frozen();primary.frozen();a=allocation();verification=read(OUT/'verification.json');bindings(verification);summary=resource_summary();receipt=BASE/'resources'/(reservation+'.settlement.json')
    if read(receipt)['status']!='passed' or summary['pending_at_snapshot']:raise RuntimeError('report supervision or active reservation')
    cpu,gpu=accounting(BASE),accounting(BASE,True)
    if any(cpu[p]>CPU[p]*NS or gpu[p]>GPU[p]*NS for p in CPU):raise RuntimeError('phase limit')
    owned=set()
    for pattern in ('*.resource.json','*.journal.json'):
        for path in (BASE/'resources').glob(pattern):owned.update(identities(read(path)))
    if any(still_same_process(*item) for item in owned):raise RuntimeError('owned process remains')
    now=dt.datetime.now(dt.timezone.utc);deadline=dt.datetime.fromisoformat(a['wall_deadline_utc'])
    checkpoint=dict(status='recovery_comparison_and_regressions_settled',verification=binding(OUT/'verification.json'),reporting_settlement=binding(receipt),resources=summary,
        cpu_phase_ns=cpu,gpu_phase_ns=gpu,active_reservations=[],live_owned_identities=[],owned_identities=len(owned),tests=verification['tests'],documentation_pages=verification['documentation_pages'],
        settled_utc=now.isoformat(),elapsed_from_followup_start_seconds=(now-(deadline-dt.timedelta(hours=2))).total_seconds(),within_two_hours=now<=deadline)
    put(OUT/'settled-checkpoint.json',checkpoint);target=DOCS/'lp-sp-pricing-recovery-checkpoint.json';target.write_text(json.dumps(checkpoint,indent=2,sort_keys=True)+'\n');(ROOT/'book/docs/benchmarks'/target.name).write_bytes(target.read_bytes())
    print(json.dumps(dict(status=checkpoint['status'],cpu_seconds=summary['cpu_ns']/NS,gpu_seconds=summary['gpu_ns']/NS,within_two_hours=checkpoint['within_two_hours'])),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','settle']);p.add_argument('--identity',default='recovery-report-v1');p.add_argument('--reservation');a=p.parse_args();OUT=BASE/a.identity
    verify_all() if a.action=='verify' else settle(a.reservation)
