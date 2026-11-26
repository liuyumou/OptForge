"""Audit and summarize the complete frozen study without repeating solves."""
from collections import Counter,defaultdict
import csv
import json
import math
from pathlib import Path
import shutil
import statistics
import sys
from lp_sp_pricing_budget import BASE,ROOT,binding,put
from lp_sp_pricing_campaign import read,validate,verify
from lp_sp_pricing_report import resource_summary


def development():
    result=[]
    for identity in ['cpu-ladder-v1','cpu-ladder-v2','cpu-ladder-v3','cpu-ladder-v4','gpu-ladder-v1','gpu-ladder-v2']:
        path=BASE/identity/'result.json';rows=read(path)['rows']
        for row in rows:verify(row['result'])
        old=[r for r in rows if '-16-' not in r['id']]
        result.append(dict(identity=identity,cells=len(rows),certified=sum(r['accepted'] for r in rows),
            capped_seconds=sum(min(r['elapsed_ns']/1e9,10) for r in rows),
            original_fourteen_certified=sum(r['accepted'] for r in old),
            original_fourteen_capped_seconds=sum(min(r['elapsed_ns']/1e9,10) for r in old),evidence=binding(path)))
    return result


def report(identity,freeze):
    out=BASE/identity;out.mkdir(exist_ok=False)
    f=read(freeze);validate(f)
    if not (freeze.parent/'completed.json').exists():raise RuntimeError('confirmation is not finished')
    rows=[];family_evidence=[]
    for family in ['dense','irregular','wide','tall','coupled','ill_scaled','degenerate']:
        path=freeze.parent/(family+'-audit.json');data=read(path);family_evidence.append(binding(path));rows+=data['rows']
    recovery=BASE/'confirmation-recovery-v1'
    if (recovery/'freeze.json').exists():
        if not (recovery/'completed.json').exists():raise RuntimeError('untouched-cell recovery is not finished')
        extra=read(recovery/'audit.json')['rows'];originals={r['cell']:r for r in rows}
        for row in extra:
            if originals[row['cell']]['attempted']:raise RuntimeError('recovery repeated a scientific identity')
            originals[row['cell']]=row
        rows=list(originals.values());family_evidence += [binding(recovery/'freeze.json'),binding(recovery/'audit.json')]
    if len(rows)!=252 or len({r['cell'] for r in rows})!=252:raise RuntimeError('full 252-cell roster required')
    if {r['cell'] for r in rows}!={c['id'] for c in f['cells']}:raise RuntimeError('frozen roster changed')
    for row in rows:
        for key in ['response','audit']:
            if row.get(key):verify(row[key])
        if row.get('audit'):
            audit=read(row['audit']['path'])
            if audit['accepted']!=row['accepted']:raise RuntimeError('acceptance changed')
            if audit['accepted'] and (audit.get('tolerance')!=1e-9 or not audit['proofs'][0]['accepted']):
                raise RuntimeError('missing strict original-model proof')
    lanes={};proof_diagnostics={}
    for lane in f['models'][0]['lanes']:
        subset=[r for r in rows if r['lane']==lane]
        lanes[lane]=dict(slots=len(subset),attempted=sum(r['attempted'] for r in subset),
            timely_certified=sum(r['accepted'] and r['timely'] for r in subset),
            late_certified=sum(r['accepted'] and not r['timely'] for r in subset),
            exact_rational_certified=sum(bool(r.get('exact',{} ) and r['exact']['accepted']) for r in subset),
            statuses=dict(Counter(str(r['status']) for r in subset)),
            confirmed_gpu_attempts=sum(bool(r.get('gpu_confirmed')) for r in subset))
        proofs=[read(r['audit']['path'])['proofs'][0] for r in subset
                if r.get('audit') and read(r['audit']['path']).get('proofs')]
        proof_diagnostics[lane]=dict(endpoints_with_strict_proof=len(proofs),
            primal_feasible=sum(p['feasible'] for p in proofs),
            without_finite_dual_bound=sum(p['bound'] is None for p in proofs))
    phase_shares={}
    models={m['id']:m for m in f['models']}
    for size in ['small','medium']:
        subset=[r for r in rows if r['lane']=='practical' and r['attempted']
                and models[r['model']]['size']==size and r.get('native_ns')]
        phase_shares[size]=dict(attempts=len(subset),
            median_completed_queries=statistics.median(r['queries'] for r in subset),
            median_phase_share={phase:statistics.median((r.get('phases') or {}).get(phase,0)/r['native_ns'] for r in subset)
                                for phase in ['market','auxiliary_labels','calibration']})
    lookup={(r.get('model'),r.get('repetition'),r['lane']):r for r in rows if r['attempted']}
    comparisons=[]
    for baseline in ['retained_image_v11','copt_scale_off']:
        pairs=[];per_model=defaultdict(list)
        for model in f['models']:
            for rep in range(3):
                left=lookup.get((model['id'],rep,'practical'));right=lookup.get((model['id'],rep,baseline))
                if left and right and all(r['accepted'] and r['timely'] for r in (left,right)):
                    ratio=right['complete_ns']/left['complete_ns'];per_model[model['id']].append(ratio)
                    pairs.append(dict(model=model['id'],repetition=rep,baseline_over_practical=ratio,
                                      practical_ns=left['complete_ns'],baseline_ns=right['complete_ns']))
        complete_models={m:statistics.median(v) for m,v in per_model.items() if len(v)==3}
        comparisons.append(dict(baseline=baseline,jointly_timely_repetitions=len(pairs),
            complete_three_repetition_models=len(complete_models),
            paired_repetition_median_ratio=statistics.median([p['baseline_over_practical'] for p in pairs]) if pairs else None,
            three_repetition_model_median_ratios=complete_models,pairs=pairs,
            broad_superiority_established=False))
    prior=ROOT/'docs/benchmarks/lp-sp-pricing-results.json'
    if prior.exists():
        shutil.copyfile(prior,out/'prototype-results.json')
        shutil.copyfile(ROOT/'docs/benchmarks/lp-sp-pricing-checkpoint.json',out/'prototype-checkpoint.json')
        shutil.copyfile(ROOT/'docs/benchmarks/lp-sp-pricing.md',out/'prototype-report.md')
    result=dict(schema=2,status='frozen_original_lp_evaluation_complete',freeze=binding(freeze),families=family_evidence,
        original_models=28,repetitions=3,slots=252,lanes=lanes,comparisons=comparisons,rows=rows,
        strict_proof_diagnostics=proof_diagnostics,practical_phase_shares=phase_shares,
        selected_configuration=f['configuration'],development=development(),resources=resource_summary(),
        native_admission=binding(BASE/'gpu-admission-v5.json'),gpu_quality_combinations=224,
        gpu_sanitizers=['memcheck','racecheck','initcheck','synccheck'],cpu_component_tests=35,
        native_exact_sanitizers=binding(BASE/'auxiliary-sanitizers-v2/binding.json'),
        native_market_sanitizers=binding(BASE/'flow-market-sanitizers-v1/binding.json'),
        reference=dict(integration_present=True,literal_end_to_end_validated=False,
            reason='literal parameters and recursion exceed admitted resource bounds',strongly_polynomial_claim=False),
        billion=read(BASE/'protocol-v1.json')['billion'],
        limitations=['three repetitions; caches not flushed; one GPU and host',
            'six families recovered in CPU/GPU blocks after setup failures; cross-lane interleaving is lost, so timing comparisons are descriptive',
            'strict 1e-9 and exact-rational certificate tiers are distinct',
            'on free-variable models, a floating dual stationarity residual can prevent a finite rigorous bound even when vendor status is optimal',
            'FP4 is simulated E2M1 components on CUDA cores, without packed storage or tensor-core claims',
            'original sparse matrices can produce dense explicit rational bases',
            'peak_bits records host-observed exact values; native rational intermediates obey the configured bit stop',
            'complete cost includes model encoding, cold process, output and all mandatory independent endpoint audits',
            'no timing ratio is assigned to a deadline, unsupported or uncertified comparison'])
    put(out/'result.json',result)
    path=ROOT/'docs/benchmarks/lp-sp-pricing-results.json';path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    fields=['cell','lane','model','family','repetition','attempted','status','accepted','timely','native_ns','process_ns','input_encoding_ns','audit_ns','complete_ns']
    with (ROOT/'docs/benchmarks/lp-sp-pricing-confirmation.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    lines=['# Pricing LP: implementation and completed evaluation','','Date: 2026-11-25.','',
        '**The CPU bottleneck is substantially reduced. The complete frozen comparison is measured; broad end-to-end superiority is not established.**','',
        'The [reference integration](../../research/lp-sp-pricing/python/sp_pricing/reference.py) connects symbolic log compression, calibration, implicit expert cells, rational ellipsoid optimization, recursive prices and sequential circuit recovery. Component tests pass; no complete literal paper run fits the admitted resource limits. The practical variant has exact original-model certificates and does not inherit the paper’s strongly polynomial guarantee.','',
        'See the [plan](../plans/lp-sp-pricing.md), [implementation](../../research/lp-sp-pricing/README.md), [compact evidence](lp-sp-pricing-results.json), and [all confirmation rows](lp-sp-pricing-confirmation.csv).','',
        '## CPU cost and implementation changes','',
        'Profiles showed that repeated Fraction operations while evaluating experts consumed about 85–90% of the profiled small solves. Shared integer denominators remove that work. An exact signed-network flow formulation replaces the finite market’s repeated LP cuts; exact flow balance and primal–dual objective equality check every market optimum. Residual-potential constraints recover lexicographic prices. This practical flow oracle is not presented as a strongly polynomial replacement for the reference ellipsoid.','',
        'The next bottleneck was auxiliary LP work. A persistent GMP tableau now reuses its basis across objectives and stops immediately on an exact positive-label witness. Native exact elimination, sparse proof products and the calibration’s proved quadratic-error bound reduce preparation and checking. Negative labels still require an exact bound or an exactly checked opposite-slot witness. Final original-model acceptance is unchanged.','',
        '| Development version | Original 14 cases certified | Capped total seconds |','| --- | ---: | ---: |']
    for item in result['development']:
        lines.append(f"| {item['identity']} | {item['original_fourteen_certified']}/14 | {item['original_fourteen_capped_seconds']:.3f} |")
    lines += ['', 'The table is a separate-seed development series, with one diagnostic measurement per version and a ten-second cap per case. It is not a randomized solver comparison. The final 21-case selection chose CPU over GPU by the frozen rule: maximize timely exact certificates, then minimize capped complete cost.','',
        'The held-out attempt timings locate the remaining bottleneck. Median phase shares include interrupted work and describe cost, not convergence:', '',
        '| Size | Market share | Auxiliary-label share | Calibration share | Median completed queries |',
        '| --- | ---: | ---: | ---: | ---: |']
    for size,item in phase_shares.items():
        shares=item['median_phase_share']
        lines.append(f"| {size} | {shares['market']:.1%} | {shares['auxiliary_labels']:.1%} | {shares['calibration']:.1%} | {item['median_completed_queries']:g} |")
    lines += ['',
        '## Frozen original-LP comparison','',
        'All 28 original models and 252 lane/repetition slots remain visible. Seven families, 16/64 variables, two held-out seeds and three repetitions compare the practical candidate, unchanged image-v11 and COPT scale-off GPU PDLP. Native windows are 10/30 seconds; process windows are 30/60 seconds. Ratios require both endpoints to pass the unchanged original-model 1e-9 checker before their deadlines. Exact rational acceptance is additionally reported for the candidate.','',
        '| Lane | Attempted / slots | Timely strict certificates | Late strict certificates |','| --- | ---: | ---: | ---: |']
    for lane,item in lanes.items():lines.append(f"| {lane} | {item['attempted']}/{item['slots']} | {item['timely_certified']} | {item['late_certified']} |")
    for item in comparisons:
        ratio=item['paired_repetition_median_ratio'];description='No ratio is defined.' if ratio is None else f"The median baseline/candidate complete-cost ratio is {ratio:.3f}x on those repetitions."
        if ratio is not None and ratio<1:
            description += f" The candidate takes about {1/ratio:.2f} times the baseline's complete cost."
        lines += ['',f"Against {item['baseline']}: {item['jointly_timely_repetitions']} jointly timely certified repetitions, covering {item['complete_three_repetition_models']} models with all three repetitions. {description}"]
    lines += ['', 'Vendor status and strict certificate acceptance are separate. On these free-variable models, a nonzero floating dual stationarity residual can prevent a finite rigorous bound. A reported optimal status is retained even when the unchanged checker cannot certify it; this does not establish that the vendor optimum is wrong.', '',
        '| Lane | Endpoints independently assessed | Primal feasible | No finite strict dual bound |',
        '| --- | ---: | ---: | ---: |']
    for lane,item in proof_diagnostics.items():
        lines.append(f"| {lane} | {item['endpoints_with_strict_proof']} | {item['primal_feasible']} | {item['without_finite_dual_bound']} |")
    lines += ['', 'Complete cost includes common model encoding, a fresh solver process, output transport and all mandatory independent endpoint audits. GPU idle observation and resource finalization are outside the comparable window but remain charged to the allocation. COPT import/preparation and its opaque solve call are separately retained.','',
        'A campaign output-parent error consumed six failed solve reservations before any LP in those families started. Every full charge remains. Recovery uses only untouched cells, with identical numerical sources, models and process windows. To stay within the unchanged phase allocation, the six recovered families execute CPU candidates and GPU baselines in separate blocks. They retain three repetitions and per-lane order, but lose the original cross-lane interleaving. The degenerate family retains the original rotation. All timing ratios are therefore descriptive; unflushed caches and unmatched certificates further limit generalization.','',
        '## GPU findings and scale limits','',
        'Dense and CSR GPU products share one matrix across batches of 1/8/32/64 independent states, now searching both signed slots. Exact checks accept witnesses and bounds; unresolved coordinates escalate and fall back to exact CPU work. Final admission passes 224 configuration checks and all four CUDA sanitizers. Both native CPU components pass ASan/UBSan and independent differential tests. The 35 mathematical/component tests include symbolic compression restarts, grouped cell sums, actual grouped-market optimization, ellipsoid feasibility/lexicographic recovery and sequential circuits.','',
        'The earlier 167/168 completed batching cells remain historical throughput evidence, including the incomplete cell that was never retried. The FP64 width-64 diagnostic measured 37.6x dense and 43.7x CSR proposal throughput versus sequential proposals. That structured resident-matrix diagnostic excludes exact checking and is not an original-LP speedup. FP4 uses simulated E2M1 components on CUDA cores; packed FP4 and tensor-core throughput are not claimed.','',
        'Both proposed original billion-nonzero LPs remain unsupported before generation. Explicit mixed-optimality bases and their transposes alone require about 804 GB for the dense case and 800 TB for the sparse case. Original sparsity does not prevent null-space fill. The held-out practical capacity refusals are also retained, alongside baseline measurements on those models.','',
        '## Evidence and resources','',
        'All failed reservations keep their full charges and original receipts. The baseline adapter failures exposed a missing model identity and a missing verified lease handoff; their failures remain, and admission subsequently sealed the exact endpoint conventions using retained development proofs. The original project numerical sources, scientific identities and public defaults are unchanged. No historical billion experiment was repeated.','',
        'The [settled checkpoint](lp-sp-pricing-checkpoint.json) records final allocation use, failures and cleanup identities. The earlier prototype report and compact receipts are preserved under the new report’s artifact directory.','']
    (ROOT/'docs/benchmarks/lp-sp-pricing.md').write_text('\n'.join(lines))
    print(json.dumps(dict(status=result['status'],lanes=lanes,comparisons=[{k:v for k,v in c.items() if k!='pairs'} for c in comparisons])),flush=True)


if __name__=='__main__':report(sys.argv[1],Path(sys.argv[2]))
