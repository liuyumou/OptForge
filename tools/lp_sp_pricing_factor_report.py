"""Preparation-inclusive factorized geometry report and settled receipt."""
import argparse
import csv
import datetime as dt
import json
from pathlib import Path
import re
import statistics as stats
import subprocess
import sys
import unittest
from lp_sp_pricing_budget import ROOT,BASE,NS,put,binding,accounting
from lp_sp_pricing_factor_budget import CPU,GPU,allocation
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_factor_experiment import STUDY as PRIMARY,validate as primary
from lp_sp_pricing_transform_experiment import STUDY as FOLLOWUP,validate as followup
from lp_sp_pricing_report import resource_summary
from lp_sp_pricing_finish import identities,still_same_process

OUT=BASE/'factor-report-v1';DOCS=ROOT/'docs/benchmarks'


def rows_for(study,count,prefix):
    rows=[];receipts=[]
    for index in range(count):
        path=BASE/'resources'/f'{prefix}{index:02d}-v1.settlement.json' if prefix=='factor-comparison-' else BASE/'resources'/f'{prefix}{index}-v1.settlement.json'
        receipt=read(path);group=read(study/f'group-{index}.json')
        eligible=receipt['status']=='passed' and receipt['cleanup_empty'] and not receipt['overrun']
        if group['status']!='all_slots_disposed':raise ValueError('unfinished group')
        for source in group['rows']:
            row=dict(source,timing_eligible=eligible,cohort='primary' if study==PRIMARY else 'optimized_holdout')
            if row['accepted']:
                proof=read(row['proof']['path'])
                if not proof['accepted'] or proof['visited_nonzeros']!=row['nonzeros'] or not proof['primal_feasible']:raise ValueError('incomplete exact proof')
                if proof.get('kind')=='rigorous_implicit_exact_dual':
                    if not proof['supported_on_exactly_active_rows'] or not proof['inverse_proof']['accepted'] or proof['inverse_proof']['error_upper']>=1 or proof['minimum_selected_dual_base']<proof['correction_infinity_upper']:raise ValueError('implicit proof margin')
                elif not proof.get('dual_equations') or not proof.get('zero_gap'):raise ValueError('explicit proof')
            rows.append(row)
        receipts.append(binding(path))
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('duplicate rows')
    return rows,receipts


def pairs(rows,models,candidate,controls):
    result=[]
    for model in models:
        selected={r['lane']:r for r in rows if r['family']==model['name'] and r['seed']==model['seed']}
        for control in controls:
            a,b=selected[candidate],selected[control]
            eligible=all(r['timing_eligible'] and r['timely'] and r['accepted'] for r in (a,b))
            result.append(dict(family=model['name'],seed=model['seed'],candidate=candidate,control=control,eligible=eligible,
                candidate_seconds=a['complete_ns']/NS,control_seconds=b['complete_ns']/NS,
                control_over_candidate=b['complete_ns']/a['complete_ns'] if eligible else None))
    return result


def development_provenance():
    plan=read(BASE/'factor-development-v1/plan.json');reservation=read(BASE/'resources/factor-development-v1.reservation.json');result=[]
    for original in plan['sources']:
        observed=binding(original['path'])
        if observed['sha256']==original['sha256']:retained=observed
        else:
            match=next(s for s in reservation['sources'] if s['path']==original['path'] and s['sha256']==original['sha256'])
            retained=binding(match['retained'])
            if retained['sha256']!=original['sha256'] or retained['bytes']!=original['bytes']:raise ValueError('development source missing')
        result.append(dict(original_path=original['path'],verified_source=retained))
    return result


def report():
    p=primary();f=followup();allocation();OUT.mkdir(exist_ok=False)
    first,receipts=rows_for(PRIMARY,15,'factor-comparison-');second,more=rows_for(FOLLOWUP,3,'transform-comparison-')
    if len(first)!=60 or len(second)!=48:raise ValueError('full frozen roster coverage')
    primary_pairs=pairs(first,p['models'],'candidate',['copt-gpu-1e9','copt-auto'])
    optimized_pairs=pairs(second,f['models'],'optimized',['factor','copt-gpu-1e9'])
    optimized_pairs+=pairs(second,[m for m in f['models'] if m['scaled']],'optimized',['copt-gpu-scaling-auto'])
    controls=[]
    for model in p['models']:
        if model['m']!=model['n']:continue
        selected={r['lane']:r for r in first if r['family']==model['name'] and r['seed']==model['seed']};a,b=selected['candidate'],selected['previous']
        da,db=read(a['response']['path']),read(b['response']['path'])
        controls.append(dict(family=model['name'],seed=model['seed'],same_exact_certificate=da.get('certificate')==db.get('certificate'),
            same_route=da.get('route')==db.get('route'),both_accepted=a['accepted'] and b['accepted'],
            candidate_over_previous_native=a['native_ns']/b['native_ns'],candidate_over_previous_complete=a['complete_ns']/b['complete_ns']))
    challenge=BASE/'factor-certificate-challenge-v1/result.json'
    if read(challenge)['status']!='passed' or read(BASE/'resources/factor-certificate-challenge-v1.settlement.json')['status']!='passed':raise ValueError('challenge supervision')
    phases=[]
    for row in first+second:
        response=read(row['response']['path']) if row.get('response') else {}
        phases.append(dict(id=row['id'],proposal=response.get('proposal'),geometry=response.get('geometry_diagnostics'),vendor_profile=response.get('profile'),
            parameters=response.get('parameters'),gpu_confirmed=response.get('gpu_confirmed'),process_hwm_bytes=response.get('process_hwm_bytes')))
    result=dict(status='complete_factorized_geometry_comparison',primary_freeze=binding(PRIMARY/'freeze.json'),followup_freeze=binding(FOLLOWUP/'freeze.json'),
        rows=first+second,primary_pairs=primary_pairs,optimized_pairs=optimized_pairs,square_controls=controls,phases=phases,
        settlements=receipts+more,selection=binding(BASE/'transform-selection-v1/result.json'),selection_seal=f.get('selection_seal'),selection_timings_eligible=f.get('selection_timings_eligible',True),challenge=binding(challenge),
        geometry_profile=binding(BASE/'factor-geometry-profile-v1/result.json'),inverse_profile=binding(BASE/'factor-inverse-profile-v1/result.json'),
        development=binding(BASE/'factor-development-v1/result.json'),development_source_provenance=development_provenance(),
        source=binding(__file__),resources_at_report=resource_summary(),
        timing_scope='Model encoding + cold solver process including all preparation + unchanged raw strict audit + cold common reconstruction + cold independent complete original-model proof. Idle/admission/settlement and corruption challenges excluded from performance, retained in accounting.',
        limitations=['Synthetic dyadic feasible bounded LPs with planted short-dyadic primal coordinates; construction witnesses never passed to solvers.',
            'Three fresh inputs per family, one cold timing each, rotated order, no cache flushing; medians are descriptive, not confidence intervals.',
            'Implicit exact dual certificate is a distinct representation; unchanged raw 1e-9 checker outcomes remain separate.',
            'Opt-in practical certified presolve, not a completed strongly-polynomial paper algorithm. Eligible tall proposals can remain inconclusive.',
            'Square dispatch remains unchanged and is measured; wide dispatch remains unchanged but has no fresh timing control here.'],
        report_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    result['checked_bindings']=bindings(result)+bindings(p)+bindings(f)
    put(OUT/'result.json',result);(DOCS/'lp-sp-pricing-factor-results.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    columns=['cohort','id','family','seed','lane','nonzeros','status','timely','timing_eligible','raw_strict_accepted','accepted','native_ns','encoding_ns','process_ns','raw_audit_ns','postprocess_ns','proof_ns','complete_ns']
    with (DOCS/'lp-sp-pricing-factor-comparison.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader();writer.writerows({k:r.get(k) for k in columns} for r in first+second)
    write_document(result,p,f)
    return result


def med(rows,key='complete_ns'):
    values=[r[key]/NS for r in rows if r['accepted'] and r['timely'] and r.get('timing_eligible',True)]
    return '—' if not values else f'{stats.median(values):.3f} ({min(values):.3f}–{max(values):.3f})'


def write_document(result,p,f):
    selection=read(result['selection']['path']);challenge=read(result['challenge']['path'])
    first=[r for r in result['rows'] if r['cohort']=='primary'];second=[r for r in result['rows'] if r['cohort']=='optimized_holdout']
    lines=['# Factorized tall geometry and exact certificate evaluation','',
        'The opt-in tall presolve avoids the rational slack-space RREF. It proposes a solution using resident GPU projections and proves an implicit exact dual correction against every original constraint. Public solver defaults and the previous numerical sources remain unchanged.','',
        '[All 108 holdout/control outcomes](lp-sp-pricing-factor-comparison.csv), [full results and phase evidence](lp-sp-pricing-factor-results.json), [preceding scale study](lp-sp-pricing-scale.md).','',
        '## Exact geometry bottleneck','',
        'The old rectangular least-squares presolve fits inactive inequalities as equalities. When its exact primal reconstruction fails, the fallback constructs an (n+1) by (m+1) slack-space matrix and performs GMP Gauss–Jordan reduction. Normalizing pivots and eliminating each new pivot from previous rows cause rational bit growth, fill and repeated map/allocation work. The earlier implicit null-space representation is built after that reduction, so it cannot remove this bottleneck.','',
        'Fresh scaling diagnostics show 330-bit intermediate rationals and 932,733 counted operations for a 64-column fixture; its exact RREF takes 1.755 seconds. The 128- and 256-column reductions hit their eight-second limits. Native failure does not return internal counters, so missing counters are not zero work. The factorized alternatives certify all five diagnostic sizes. Geometry-only and complete-solve timings are distinct quantities.','',
        '## Implemented paths','',
        'For eligible tall shapes (m >= 2n, n <= 4096, mn <= 2^27), the new numerical proposal factors G=AᵀA once. ADMM projection batches keep A, G and state on the GPU. The separately implemented precomputed representation stores A G⁻¹ and removes triangular solves from each iteration, at the cost of another mn FP64 entries. Both representations are proposals; neither accepts a certificate. Shapes outside this dispatch retain the previous solver.','',
        f'The finite development selection tried both representations and penalty multipliers 1, 4, 16 and 64 on separate inputs at three scales. It wrote all 24 results and an exploratory choice, but final resource supervision failed with coordinator_lost. Its full 2400 CPU / 600 GPU-second charge remains; cleanup is empty, no overrun is recorded, and the preceding cause is unknown. A separately supervised read-only seal preserves the completed records without regrading supervision or repeating solves. Sweep timings are excluded from performance evidence. The retained hypothesis is **{selection["representation"]}, multiplier {selection["rho_multiplier"]}**; independent untouched holdouts evaluate it. Those fifteen models use different seeds and additionally test row-scaled tall and dense square cases.','',
        'The optimized common postprocessor directly proposes an implicit tall certificate, avoids the unsuccessful short-dual ladder, and leaves inverse-bound acceptance to the independent checker once. Two numerical dual-refinement steps reduce the residual before the dyadic base is checked; they carry no acceptance authority. Small inverse proposals remain on CPU: the cold 2000-column microbenchmark takes 0.509 seconds on CPU versus 0.657 seconds on GPU. Larger inverse proposals use GPU. The independent checker uses three integer-scan workers while the parent evaluates the inverse enclosure; all partial products are combined with unbounded integers.','',
        '## Certificate definition and authority','',
        'Let x be an exactly feasible dyadic primal point and y₀ a nonnegative dyadic dual base supported only on exactly active rows. Choose n active rows with positive y₀ and let B contain those rows of A. The certificate defines δ by Bᵀδ=c−Aᵀy₀ and y=y₀+Eδ. It does not store enormous rational inverse entries.','',
        'An approximate inverse R is untrusted evidence. The CPU checker bounds q=‖I−RBᵀ‖∞ using an independent FP64 product, a conservative γ_(2n+1) roundoff allowance and underflow allowance. If q<1, B is nonsingular and ‖(Bᵀ)⁻¹‖∞≤‖R‖∞/(1−q). Exact integer residuals then bound ‖δ‖∞. If this bound is at most the smallest selected y₀, the corrected dual is nonnegative. Exact stationarity and support on active rows imply exact zero gap.','',
        'All primal inequalities, active support and residuals are checked on the complete original CSR with arbitrary-precision integers. The enclosure assumes standard IEEE FP64 BLAS arithmetic; non-nearest CPU rounding is rejected. Small exact-Fraction products and solves cross-check the bound. This is a separate implicit exact-certificate tier. A raw floating endpoint can fail the unchanged 1e-9 checker while its explicitly defined corrected dual has an exact proof; those outcomes are never conflated.','',
        f'Every accepted implicit holdout/control endpoint also receives a negative-dual and zero-inverse corruption challenge: **{challenge["corruption_checks"]} checks on {challenge["certificates"]} certificates**. Zero-inverse challenges retain complete original-matrix traversal.','',
        '## Comparison design','',
        'The primary study freezes fifteen models (three seeds, five families), 45 main solver slots and 15 controls. Tall sizes are 4000×1000 / 1M NNZ, 8000×2000 / 4M NNZ and 16000×4000 / 16M NNZ, with 20% inactive rows. Square controls are dense 2000×2000 / 4M NNZ and row-scaled sparse 8000×8000 / 1M NNZ. The follow-up has fifteen fresh models and 48 slots, including row-scaled mixed-active 4M tall and dense 4M square cases. Three additional GPU COPT controls preserve installed default Scaling on the row-scaled tall models, with otherwise identical PDLP settings. All inputs are synthetic signed dyadics; planted construction witnesses are independently checked but never supplied to solvers.','',
        'Each solver receives a 60-second native allowance and a 90-second process allowance. The primary GPU control uses inherited scale-off COPT PDLP settings except PDLPTol=1e-9, matching the required raw tolerance. The inherited PDLPTol=1e-12 control remains on the first seed at every tall size. COPT automatic CPU settings remain unchanged. All candidates and vendor endpoints receive the same postprocessor within their cohort. COPT is configured for four CPU threads; candidate BLAS is one thread and the optimized independent checker uses the four reserved CPU slots.','',
        'Complete times below include common model encoding, cold process startup, input/hash checks, all CPU/GPU preparation, solving, teardown, the unchanged raw strict audit, common reconstruction and a cold full independent proof. COPT internal GPU preparation remains in its solve call. Idle admission, resource settlement and extra corruption challenges are excluded from performance times and retained in total resource accounting. Unsuccessful timings remain in the CSV and never become certified speedup ratios.','',
        '## Primary results','',
        '| Family | Candidate certified / 3 | Candidate complete seconds: median (range) | GPU COPT eligible pairs / 3 | CPU COPT eligible pairs / 3 |',
        '| --- | ---: | ---: | ---: | ---: |']
    for model in p['models'][:5]:
        family=model['name'];candidate=[r for r in first if r['family']==family and r['lane']=='candidate']
        eligible=lambda control:sum(q['eligible'] for q in result['primary_pairs'] if q['family']==family and q['control']==control)
        lines.append(f'| {family} | {sum(r["accepted"] and r["timely"] and r["timing_eligible"] for r in candidate)}/3 | {med(candidate)} | {eligible("copt-gpu-1e9")}/3 | {eligible("copt-auto")}/3 |')
    lines+=['','The first-seed CPU controls isolate the projection cost. Their shared final proof policy is unchanged; at 4000 columns it may use a GPU inverse proposal even when the solver projection runs on CPU.','',
        '| Tall family | GPU numerical projection seconds | CPU numerical projection seconds | CPU exact certificate | Previous path solve seconds / outcome |',
        '| --- | ---: | ---: | --- | --- |']
    for model in p['models'][:3]:
        selected={r['lane']:r for r in first if r['family']==model['name'] and r['seed']==model['seed']}
        gpu,cpu,old=selected['candidate'],selected['candidate-cpu'],selected['previous']
        def numerical(row):
            detail=row.get('proposal') or {};value=detail.get('complete_ns');return '—' if value is None else f'{value/NS:.3f}'
        previous='—' if old['native_ns'] is None else f'{old["native_ns"]/NS:.3f}'
        lines.append(f'| {model["name"]} | {numerical(gpu)} | {numerical(cpu)} | {cpu["accepted"] and cpu["timely"]} | {previous} / {old["status"]} |')
    lines+=['','Previous-path deadlines are unsuccessful outcomes, not measured speedup denominators.','', '## Fresh optimized holdout','',
        '| Family | Optimized complete seconds | Factor control complete seconds | COPT GPU complete seconds | Eligible COPT pairs / 3 | Median COPT / optimized |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for model in f['models'][:5]:
        family=model['name'];group=[r for r in second if r['family']==family]
        qs=[q for q in result['optimized_pairs'] if q['family']==family and q['control']=='copt-gpu-1e9' and q['eligible']]
        ratio='—' if not qs else f'{stats.median(q["control_over_candidate"] for q in qs):.3f}×'
        lines.append(f'| {family} | {med([r for r in group if r["lane"]=="optimized"])} | {med([r for r in group if r["lane"]=="factor"])} | {med([r for r in group if r["lane"]=="copt-gpu-1e9"])} | {len(qs)}/3 | {ratio} |')
    lines+=['','Cold independent CPU checker controls use identical certificates; exact residuals and acceptance decisions agree, and both inverse enclosures validate:','',
        '| Nonzeros | Parallel complete seconds | Serial complete seconds | Serial / parallel |',
        '| ---: | ---: | ---: | ---: |']
    for control in challenge['serial_controls']:
        lines.append(f'| {control["nonzeros"]:,} | {control["parallel_process_ns"]/NS:.3f} | {control["serial_process_ns"]/NS:.3f} | {control["serial_over_parallel"]:.3f}× |')
    lines+=['','These are one-time, later serial controls without cache flushing. Their extra audit costs remain in resource accounting and do not replace the original measured pipeline.','']
    same=result['square_controls'];total=sum(q['eligible'] for q in result['primary_pairs']);fresh=sum(q['eligible'] for q in result['optimized_pairs'] if q['control']=='copt-gpu-1e9')
    lines+=['','Default-scaling COPT GPU controls on the scaled tall family:','',
        '| Seed | Both exact and timely | Optimized complete seconds | Default-scaling COPT complete seconds | COPT / optimized |',
        '| ---: | --- | ---: | ---: | ---: |']
    for q in result['optimized_pairs']:
        if q['control']!='copt-gpu-scaling-auto':continue
        ratio='—' if not q['eligible'] else f'{q["control_over_candidate"]:.3f}×'
        lines.append(f'| {q["seed"]} | {q["eligible"]} | {q["candidate_seconds"]:.3f} | {q["control_seconds"]:.3f} | {ratio} |')
    lines+=['',f'The primary cohort has {total}/30 eligible candidate–COPT pairs; the fresh optimized cohort has {fresh}/15 eligible optimized–COPT pairs. Counts refer to their own prospective common exact-certificate pipelines, not raw endpoint acceptance or pooled timing repetitions.','',
        f'All {len(same)} square old/new controls have identical exact certificates: {all(r["same_exact_certificate"] for r in same)}. The median new/old native-time ratio is {stats.median(r["candidate_over_previous_native"] for r in same):.3f}; the complete-time ratio is {stats.median(r["candidate_over_previous_complete"] for r in same):.3f}. Single timings have noise; individual ratios and regressions remain in the full results. Wide dispatch is unchanged but has no fresh timing measurement here.','',
        '## Limits and reproduction','',
        'These results establish performance and exact proof validity for the represented synthetic inputs. They do not establish broad LP superiority, infeasible/unbounded-case coverage for the new tall presolve, or completion of the paper’s strongly-polynomial algorithm. The three seeds are descriptive samples, not a broad workload distribution. Ill-conditioned or unsupported implicit reconstructions can remain inconclusive.','',
        f'The optimized numerical entry point is `tools/lp_sp_pricing_transform_run.py MODEL OUTPUT --representation {selection["representation"]} --rho-multiplier {selection["rho_multiplier"]}`. The common postprocessor is `tools/lp_sp_pricing_transform_endpoint.py`; independent acceptance is `tools/lp_sp_pricing_factor_parallel_proof.py`. Run GPU commands only with an appropriate fresh admitted resource reservation. Frozen plans, source hashes, exact parameters, all outcomes and every original failure charge remain in the local evidence.','',
        'The two-hour deadline and unchanged 240000 CPU / 30000 GPU-second total ceilings govern this study. Final tests, all CUDA sanitizer receipts, settlement and owned-process absence are recorded in the compact checkpoint. No historical scientific cell was repeated.','']
    (DOCS/'lp-sp-pricing-factor.md').write_text('\n'.join(lines))


def verify_all():
    result=report();suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'),'test_lp_sp_pricing*.py')
    outcome=unittest.TextTestRunner(verbosity=2).run(suite)
    if not outcome.wasSuccessful() or outcome.skipped or outcome.testsRun!=112:raise RuntimeError('final regression suite')
    for pattern in ('lp_sp_pricing_factor*.py','lp_sp_pricing_transform*.py'):
        for path in (ROOT/'tools').glob(pattern):compile(path.read_text(),str(path),'exec')
    docs=subprocess.run([sys.executable,'-B',str(ROOT/'tools/build_docs.py')],cwd=ROOT,text=True,capture_output=True,check=True)
    print(docs.stdout,end='',flush=True);match=re.search(r'documentation built: (\d+) pages',docs.stdout)
    if not match:raise ValueError('documentation receipt')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    put(OUT/'verification.json',dict(status='passed',tests=outcome.testsRun,documentation_pages=int(match[1]),result=binding(OUT/'result.json'),
        outputs=[binding(DOCS/name) for name in ('lp-sp-pricing-factor.md','lp-sp-pricing-factor-results.json','lp-sp-pricing-factor-comparison.csv')]))


def settle(reservation):
    primary();followup();approval=allocation();verification=read(OUT/'verification.json');bindings(verification);summary=resource_summary()
    if summary['pending_at_snapshot']:raise RuntimeError('active reservation')
    receipt=BASE/'resources'/(reservation+'.settlement.json')
    if read(receipt)['status']!='passed':raise RuntimeError('reporting supervision')
    cpu,gpu=accounting(BASE),accounting(BASE,True)
    if any(cpu[p]>CPU[p]*NS or gpu[p]>GPU[p]*NS for p in CPU):raise RuntimeError('phase cap')
    owned=set()
    for pattern in ('*.resource.json','*.journal.json'):
        for path in (BASE/'resources').glob(pattern):owned.update(identities(read(path)))
    if any(still_same_process(*item) for item in owned):raise RuntimeError('owned process remains')
    now=dt.datetime.now(dt.timezone.utc);deadline=dt.datetime.fromisoformat(approval['wall_deadline_utc'])
    checkpoint=dict(status='factorized_geometry_evaluation_settled',verification=binding(OUT/'verification.json'),reporting_settlement=binding(receipt),
        resources=summary,cpu_phase_ns=cpu,gpu_phase_ns=gpu,owned_identities=len(owned),live_owned_identities=[],active_reservations=[],
        tests=verification['tests'],documentation_pages=verification['documentation_pages'],settled_utc=now.isoformat(),
        elapsed_from_campaign_start_seconds=(now-(deadline-dt.timedelta(hours=2))).total_seconds(),within_two_hours=now<=deadline,wall_deadline_utc=approval['wall_deadline_utc'])
    put(OUT/'settled-checkpoint.json',checkpoint);target=DOCS/'lp-sp-pricing-factor-checkpoint.json';target.write_text(json.dumps(checkpoint,indent=2,sort_keys=True)+'\n')
    (ROOT/'book/docs/benchmarks'/target.name).write_bytes(target.read_bytes())
    print(json.dumps(dict(status=checkpoint['status'],cpu_seconds=summary['cpu_ns']/NS,gpu_seconds=summary['gpu_ns']/NS,
        elapsed_seconds=checkpoint['elapsed_from_campaign_start_seconds'],within_two_hours=checkpoint['within_two_hours'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','settle']);p.add_argument('--reservation');p.add_argument('--identity',default='factor-report-v1');a=p.parse_args()
    OUT=BASE/a.identity
    verify_all() if a.action=='verify' else settle(a.reservation)
