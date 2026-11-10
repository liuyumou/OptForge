"""Render completed native-return evidence; no model evaluation or solver calls."""
import collections
from pathlib import Path
import statistics

from lp_baseline_common_v5 import BASE, ROOT, checked, load, put, ref, require


def main():
    report_path = BASE/'report.json'
    r = load(report_path)
    rows = r['rows']
    require(len(rows)==240, 'complete planned denominator required')
    manifest = load(BASE/'manifest.json')
    configs = manifest['configurations']
    models = sorted({x['model'] for x in rows})
    machine = ROOT/'docs/benchmarks/data/external-baseline-native-result-v1.json'
    require(not machine.exists(), 'delivery already written')
    machine.write_bytes(report_path.read_bytes())
    summaries = {(x['model'],x['configuration']):x for x in r['summary']}
    cuopt = [c for c in configs if c['solver']=='cuopt']
    others = [c for c in configs if c['solver']!='cuopt']
    native = [x for x in rows if x['configuration'].startswith('cuopt-')]
    terms = collections.Counter(x.get('native_observation',{}).get('termination_reason','no durable native return') for x in native)
    native_passes = sum(x['native_return_pass'] is True for x in native)
    resource_failures = [x for x in rows if x['status']=='refused']
    counts=[]
    for c in configs:
        selected=[x for x in rows if x['configuration']==c['id']]
        counts.append('| '+c['id']+' | '+str(sum(x['status']!='unexecuted' for x in selected))+'/24 | '
            +(str(sum(x['native_return_pass'] is True for x in selected))+'/24' if c['solver']=='cuopt' else 'not this policy')
            +' | '+str(sum(x['comparison_pass'] for x in selected))+'/24 | '+str(sum(x['certified'] for x in selected))+'/24 |')
    def model_table(configurations, policy):
        text=['| Model | '+' | '.join(c['id'] for c in configurations)+' |',
              '| --- | '+' | '.join('---:' for _ in configurations)+' |']
        for model in models:
            cells=[]
            for c in configurations:
                s=summaries[(model,c['id'])]
                count=s['certified'] if policy=='certified' else s['comparison_passes']
                median=s[policy+'_median_seconds']
                cells.append(f'{median:.3f}' if median is not None else f'— ({count}/3)')
            text.append('| '+model.replace('gpup-development-','').replace('gpup-extension-','')+' | '+' | '.join(cells)+' |')
        return '\n'.join(text)
    native_times=['| Model | '+' | '.join(c['id'] for c in cuopt)+' |',
                  '| --- | '+' | '.join('---:' for _ in cuopt)+' |']
    for model in models:
        cells=[]
        for c in cuopt:
            times=[x['native_observation']['native_solve_seconds'] for x in native
                   if x['model']==model and x['configuration']==c['id'] and x['native_return_pass'] is True]
            times=[v for v in times if type(v) in (int,float)]
            cells.append(f'{statistics.median(times):.6f}' if len(times)==3 else f'— ({len(times)}/3)')
        native_times.append('| '+model.replace('gpup-development-','').replace('gpup-extension-','')+' | '+' | '.join(cells)+' |')
    quality=[]
    for c in cuopt:
        selected=[x for x in native if x['configuration']==c['id']]
        measured=[x for x in selected if x['quality'] is not None]
        def maximum(key):
            vals=[key(x) for x in measured];vals=[v for v in vals if v is not None]
            return f'{max(vals):.6g}' if vals else 'unavailable'
        reasons=collections.Counter(x.get('native_observation',{}).get('termination_reason','unavailable') for x in selected)
        quality.append('| '+c['id']+' | '+', '.join(f'{k}: {v}' for k,v in sorted(reasons.items()))+' | '
            +str(sum(x['quality']['feasible'] is True for x in measured))+'/'+str(len(measured))+' | '
            +maximum(lambda x:x['quality']['constraints']['maximum_allowance_ratio'])+' | '
            +maximum(lambda x:x['quality']['gap_upper'])+' |')
    failures=[]
    for x in resource_failures:
        observation=x.get('native_observation',{})
        trial=load(checked(x['trial']))
        settlement=load(checked(trial['settlement']))
        resource=load(checked(settlement['resource']))
        reason=(resource.get('result') or {}).get('reason','resource refusal')
        failures.append('- `'+x['id']+'`: `'+reason+'`; native termination `'
                        +observation.get('termination_reason','unavailable')+'`; native-return pass `'
                        +str(x['native_return_pass']).lower()+'`. Full certified latency is unavailable.')
    old=load(ROOT/'docs/benchmarks/data/external-baseline-final-accounting-v1.json')
    data=dict(schema_version=1,kind='lp-baseline-native-delivery-index',report=ref(report_path),machine_report=ref(machine),
        planned=240,executed=r['executed'],strict_certified=r['certified'],comparison_passes=r['comparison_passes'],
        cuopt_native_passes=native_passes,cuopt_native_terminations=dict(terms),
        resource_failures=[dict(id=x['id'],trial=x['trial'],native_return=x['native_return']) for x in resource_failures],
        prior_accounting=ref(ROOT/'docs/benchmarks/data/external-baseline-final-accounting-v1.json'),
        current_accounting='docs/benchmarks/data/external-baseline-native-accounting-v1.json',
        renderer=ref(Path(__file__)))
    put(BASE/'delivery-index.json',data)
    body=f'''# GPUP-BASELINE completion under the native-return policy

Date: 2026-11-10. Status: {'complete screening roster' if r['full_comparison_complete'] else 'incomplete screening roster'} under the user's
[native-return amendment](../decisions/ADR-0052-baseline-native-return.md).
All **{r['executed']}/240 planned cells** have settled attempts; **{r['comparison_passes']}**
meet their declared comparison policy and **{r['certified']}** meet the unchanged
independent certificate policy. These are distinct outcomes. No result is
certified merely because its solver returned normally.

The [machine report](data/external-baseline-native-result-v1.json) includes every
row, native error/status, original-model diagnostics, reference-objective
deviations, clocks, source references and paired comparisons. The
[final accounting](data/external-baseline-native-accounting-v1.json) and
[acceptance receipt](data/external-baseline-native-acceptance-v1.json) close this
continuation. The [previous report](lp-external-baseline-gpup-baseline.md), all
previous failures and every historical charge remain unchanged.

## Meaning of a pass

For cuOpt, the requested pass means a returned Solution with zero error status,
an empty error message and a recognized non-error termination. **{native_passes}/96**
cuOpt trials have that observation. Iteration/time limits are accepted native
returns under this policy, but remain limits rather than native optimality.
NumericalError is a reported error even when the separate error-code field is
zero. A native return can survive a later checker/worker failure; its pass remains
logged while its successful complete-latency observation is unavailable.

Other configurations retain strict certification for comparison acceptance.
This deliberately asymmetric policy follows the user's request. Native-return
comparisons are **not quality-matched certified speedups**. Strict certificates
still use original-model feasibility, outward dual bounds and the unchanged
absolute/relative 1e-9 gap policy. GPU confirmation remains separate, including
unknown execution for short activity samples or presolve-only returns.

| Configuration | Attempted | cuOpt native-return passes | Complete comparison passes | Strict certificates |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(counts)}

## Complete delivery times

The following medians are seconds from fresh worker launch through durable
evidence and exit. A number requires all three accepted complete repetitions;
otherwise the certified/accepted count is shown and no successful median is
reported. No failure is dropped to improve a timing.

The six retained configurations use strict certification:

{model_table(others,'certified')}

cuOpt uses the newly requested native-return policy in this separate table:

{model_table(cuopt,'comparison_pass')}

For comparison with delivery overhead, cuOpt's reported **native solve** medians
are below. They require three error-free native returns, may include ordinary
iteration/time limits, and exclude preparation, import/export and independent
checking. They are diagnostics, not substitutes for the primary timings above.
The retained project interface does not isolate an equivalent native duration.

{chr(10).join(native_times)}

Old small-model results used v2 transport; new cuOpt results use v5's compiled
validation and buffered certificate output. Those cross-cohort paired ratios are
withheld. Large-model v4 and v5 share the same numerical worker/checker pipeline;
the new cuOpt raw-status/vector output is included in its delivery cost. The
machine report labels transport and quality matching for every comparison.
Complete three-pair comparisons use median log ratios and 10000 bootstrap
resamples with seed 17111. Three repetitions do not establish broad reliability.

## Numerical differences retained honestly

These maxima summarize observed diagnostics across different models and scales;
they are not a common accuracy target or a solver ranking. The allowance ratio
is original row-side violation divided by that side's original allowance; values
above one fail that componentwise test. A gap alone is not a certificate when
feasibility fails. Missing checker results stay unavailable.

| cuOpt configuration | Native termination counts | Feasible / checker observations | Largest row allowance ratio | Largest enclosed gap |
| --- | --- | ---: | ---: | ---: |
{chr(10).join(quality)}

The machine evidence preserves available native objectives/residuals/gap, raw
vendor dual vectors and independently recomputed objective/bound/feasibility.
Missing values and partial deliveries remain explicitly unavailable.
Objective deviation from the matched project result is explicitly a deviation,
not an optimality gap when feasibility is absent. No vectors or tolerances are
silently repaired. The earlier presolve-only maximization dual-sign discrepancy
remains an unresolved adapter mapping; these observations do not prove a cuOpt
implementation defect. Native stopping rules and the project's componentwise
certificate policy also differ.

## Resource and transport failures

{chr(10).join(failures) if failures else 'No new outer resource/transport failure occurred.'}

Timeouts and failures are settled attempted cells, not successful solves. All
partial native returns, vectors, logs and cleanup records remain available.
The original 15 uncertified screening outcomes are reused, including HiGHS's
missing-candidate error mapping and COPT's strict-gap/native-limit outcomes.
They were not retried or relabeled.

## Execution, validation and scope

The continuation reused all 123 previously completed screening trials and executed
only the 117 previously unexecuted cells. No strict admission or historical
numerical check/profile was rerun. Source admission confirms unchanged original
models, solver settings, non-cuOpt adapters, original checker binary, libraries,
device and CPU affinity. The cuOpt input/settings prefix through Solve is identical;
new code captures the explicit error/status API and raw return evidence.

Nine new policy/export tests pass, including a native pass with a rejected
independent certificate and a native return surviving extraction failure. A
tenth CPU-only check exercises the installed cuOpt Solution API without Solve or
a device call. Prior tests and hardware receipts are reused. Delivery checks are
recorded in the linked acceptance receipt.

The new CPU allocation is bounded at 32000 supervisor seconds, separately from
closed historical CPU allocations. Total baseline GPU authority stays **3600
seconds**, including **{old['gpu_total_ns']/1e9:.9f}** previously charged. The settled
total is **{(old['gpu_total_ns']+sum(r['gpu_snapshot_ns'].values()))/1e9:.9f} GPU seconds**.
v5 has at most 2322 whole remaining GPU seconds; failures retain full reservations. Final
post-settlement usage is in the accounting link. Four CPU slots, one GPU lease,
the unchanged 40-second native/60-second outer limits and sampled memory/output
bounds apply throughout. The old GPU ledger is untouched.

This is a generated development LP baseline on the pinned RTX PRO 6000 Blackwell,
cuOpt 26.10.0, COPT 8.0.6 and HiGHS 1.11.0. Gurobi remains unavailable. No held-out,
MILP, general commercial-solver ranking or supported low-precision preset follows.
GPUP-8 remains incomplete and GPUP-9 remains gated. The
[roadmap](../plans/gpu-lp-precision-roadmap.md#current-plan-2026-11-10) records the next
resident-execution and simpler mixed-precision decisions.
'''
    path=ROOT/'docs/benchmarks/lp-external-baseline-native-return.md'
    require(not path.exists(),'human report already written')
    path.write_text(body)
    print('Native-return report and full machine evidence written.',flush=True)


if __name__=='__main__':
    main()
