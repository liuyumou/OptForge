"""Measured assessment/control results, limitations and local continuation state."""
import statistics
from lp_billion_common import BASE,ROOT,load,require

def main():
    data=load(ROOT/'docs/benchmarks/lp-billion-gpu-control-results.json')
    small,large=data['cohorts']
    require(small['scale']=='64m' and large['scale']=='1b','both complete control cohorts')
    def pairs(report):
        rows={r['id']:r for r in report['cells']+report['historical_controls']}
        return [(p,rows[p['baseline']],rows[p['candidate']]) for p in report['comparisons']]
    def phase(row,key):return row['complete_cost_ledger']['exclusive_ns'][key]/1e9
    def control(row):return phase(row,'original_model_control')+phase(row,'restart_weight_control')
    def timing_table(report):
        lines=['| Family | Control before / after (s) | Assessment before / after (s) | Fresh process before / after (s) | Complete before / after (s) | Updates before / after | Certified before / after |','| --- | ---: | ---: | ---: | ---: | ---: | --- |']
        for p,a,b in pairs(report):
            if not p['both_timing_eligible']:
                lines.append(f"| {p['family']} | unavailable | unavailable | unavailable | unavailable | {a.get('logical')} / {b.get('logical')} | {a.get('certified',False)} / {b.get('certified',False)} |")
                continue
            lines.append(f"| {p['family']} | {control(a):.3f} / {control(b):.3f} | {phase(a,'strict_certificate'):.3f} / {phase(b,'strict_certificate'):.3f} | {a['fresh_process_ns']/1e9:.3f} / {b['fresh_process_ns']/1e9:.3f} | {a['complete_ns']/1e9:.3f} / {b['complete_ns']/1e9:.3f} | {a['logical']} / {b['logical']} | {a['certified']} / {b['certified']} |")
        return '\n'.join(lines)
    def setup_table():
        lines=['| Billion family | Preparation before / after (s) | Device setup before / after (s) | Solver peak host RSS before / after (GiB) | Sampled owned GPU peak after (GiB) |','| --- | ---: | ---: | ---: | ---: |']
        gib=lambda v:f'{v/2**30:.3f}' if v is not None else 'unavailable'
        for p,a,b in pairs(large):
            if not p['both_timing_eligible']:continue
            lines.append(f"| {p['family']} | {a['solver_preparation_ns']/1e9:.3f} / {b['solver_preparation_ns']/1e9:.3f} | {phase(a,'device_setup'):.3f} / {phase(b,'device_setup'):.3f} | {gib(a.get('solver_child_hwm_bytes'))} / {gib(b.get('solver_child_hwm_bytes'))} | {gib(b.get('sampled_peak_owned_device_bytes'))} |")
        return '\n'.join(lines)
    admission=load(BASE/'gpu-control-gpu-v1/result.json')
    quality=load(BASE/'gpu-control-quality-v3/result.json')
    d=admission['diagnostics']
    equal=[p for p in large['comparisons'] if p['both_timing_eligible'] and p.get('same_accepted_updates')]
    equal_text=(f"The {len(equal)} equal-update historical pairs have a descriptive complete-cost median ratio of "
        f"{statistics.median(p['complete_ratio'] for p in equal):.3f}x; "
        f"{sum(p.get('exact_numerical_transcript',False) for p in equal)} have identical full transcripts. "
        'Equal update counts do not remove deadline classification or cross-run timing variability.') if equal else 'There is no timing-eligible equal-update historical pair.'
    certified=[]
    for p,a,b in pairs(large):
        if p['both_strict_certified']:
            certified.append(f"{p['family']}: {a['complete_ns']/1e9:.3f} to {b['complete_ns']/1e9:.3f} s complete ({p['complete_ratio']:.3f}x), {a['logical']} / {b['logical']} updates")
    certified_text='Jointly certified historical comparisons: '+('; '.join(certified) if certified else 'none')+'.'
    coupled=next(r for r in large['cells'] if r['family']=='coupled_blocks')
    bottlenecks='The coupled case has no eligible complete timing.'
    if coupled.get('timing_eligible'):
        costs=sorted(coupled['complete_cost_ledger']['exclusive_ns'].items(),key=lambda v:v[1],reverse=True)
        bottlenecks=f"The coupled billion case accepts {100*coupled['accepted_fp4_share']:.1f}% FP4 product work. Its largest remaining intervals are "+', '.join(f'`{k}` ({v/1e9:.3f} s)' for k,v in costs[:4])+'.'
    available=sum('response' in r for r in large['cells'])
    compact=load(BASE/'space-compaction/sources-v1/result.json')
    pruning=[load(BASE/'space-pruning'/name/'result.json') for name in ['old-large-v1','finished-large-v1']]
    released=(compact['physical_bytes_released']+sum(d['allocated_bytes_released'] for d in pruning))/2**30
    text=f'''

## GPU assessment and control with strict CPU acceptance

Opt-in image-v11 reuses the resident scaled matrices for exact-tree projected
residual products and GPU restart-movement norms. It preserves the original
1024-leaf arithmetic tree, signed-zero behavior and FP64 operations; long matrix
lines explicitly retain CPU control. The scalar square roots and log/exp weight
recurrence remain on the CPU. Reused device scratch and removed idle product
workers avoid another scaled matrix or persistent vector allocation.

Original-order primal feasibility now runs across GPU rows using original
coefficients and bounds. Original CSR indices are borrowed; original coefficients
and bounds occupy additional device memory, and bounded uploads use at most
8 MiB of new host scratch. The unchanged CPU dual-bound enclosure and gap
arithmetic remain authoritative. Every potentially accepting assessment must also
pass the original CPU feasibility check and identical objective bits before it
can grant a strict original-model 1e-9 certificate. GPU residuals never substitute
for that proof. Every final and intermediate claim receives independent CPU
checking after the measured solve.

Public defaults, original solve/preparation/packing CUDA binaries, control100,
certificate500 and recovery semantics remain unchanged. Native quality passes
{quality['rust_tests']} isolated Rust tests, formatting, Clippy, release and CUDA
compilation. Device admission passes {d['merit_comparisons']} bitwise residual
comparisons, {d['host_fallbacks']} explicit long-line fallbacks,
{d['movement_comparisons']} exact movement-norm comparisons,
{d['feasibility_comparisons']} original-feasibility comparisons and
{d['invalid_inputs_rejected']} malformed-input rejections. Deep reductions exceed
1024 squared vector entries. The {len(admission['rows'])} exact continuations cover
native, FP32, FP4x1, FP4x2, recovery and cancellation, with
{sum(len(r['serial']) for r in admission['rows'])} independent scalar checks.
All four complete sanitizers cover the diagnostic and twenty continuations each.

The fresh rotated six-family 64 M cohort retains 100 updates per cell and exact
full numerical transcripts. Descriptive median ratios (before / after) are
{small['control_ratio_median']:.3f}x control, {small['assessment_ratio_median']:.3f}x assessment,
{small['fresh_process_ratio_median']:.3f}x fresh process and {small['complete_ratio_median']:.3f}x complete cost.
The preparation ratio is {small['preparation_ratio_median']:.3f}x. All regressions
and uncertified endpoints remain in the results.

{timing_table(small)}

Six new full LP attempts each contain one billion original matrix nonzeros.
{available} return endpoints; the wide cell is interrupted without a response and
is never retried. All returned endpoints pass independent audits. They retain
the 1000-update ceiling and requested 600-second solver allowance. Their v10
controls are historical runs, so the comparison is descriptive rather than a
randomized paired billion-scale experiment. Before / after median ratios are
{large['control_ratio_median']:.3f}x control, {large['assessment_ratio_median']:.3f}x assessment,
{large['fresh_process_ratio_median']:.3f}x fresh process and {large['complete_ratio_median']:.3f}x complete cost.
Different deadline/update work is explicit. Uncertified bounded runs cannot
establish certified-solve speedups.

{timing_table(large)}

{equal_text}

{certified_text}

{bottlenecks}

{setup_table()}

Control combines `original_model_control` and `restart_weight_control`;
assessment is `strict_certificate`. Preparation includes initial control;
device setup is reported separately. Fresh process includes original input
reading/hashing/validation, CSR-to-CSC construction, solver execution and response
persistence. Complete cost additionally includes the cold independent final
original-model proof. Additional intermediate audits remain separately reported
offline costs. Every exclusive phase sums exactly to complete cost; nested timing
metrics are not counted twice. These are host elapsed intervals, not kernel-active
times. Caches were not flushed. The CSV retains all phases and observed peaks.

Device memory rises to hold the original feasibility arrays. Peak host RSS is the
solver child's high-water mark; sampled aggregate host/device peaks are distinct
measurements. Conservative capacity bounds, 4 GiB physical host headroom and all
ownership/idle checks remain enforced. The five zero-eligible families use their
established FP32 fallback; the coupled family retains actual FP4 work. Broad FP4
certified-solve superiority remains unestablished.

The user explicitly extends the open allocation to 370000 CPU / 44000 GPU seconds,
with CPU phase caps 10000/26000/58000/162000/113000/1000 and GPU caps 10000/34000.
The original recovery and both packing-transfer approvals remain required. Preserve
all failures and full charges, including CPU-v27's obsolete totals assertion and
quality-v1's formatting failure and quality-v2's diagnostic settings compile error.
No attempted scientific cell is retried. Four CPU
slots, 128 GiB host, 80 GiB owned GPU, 400 GiB storage, one-second supervision and
all 100 ms advisories stay unchanged. Remain container-only; no reset, host escape,
other-job signal or owner inference. Commit locally only, with no public adoption
or fresh full portable replay claim. The earlier general allocation is unchanged.

The wide attempt retains its full 5000 CPU / 1250 GPU-second charge and original
incomplete cleanup receipt. A later exact-identity check confirms all owned
processes gone, with no new signal; fresh CPU v29 / GPU v23 and a complete idle
window admit only the four untouched cells. The original interruption reason
was overwritten by the cleanup result and remains undetermined.

At the user's explicit request, obsolete large chunks are deleted after dependent
solves/audits finish. Source compaction verifies and archives {compact['files_compacted']}
older loose files, and new reservations share immutable source objects. Together
these actions release {released:.3f} GiB of allocated disk blocks. All small timing,
certificate, source-binding and failure records remain. Historical raw-data replay
requires regenerating deleted chunks; restoring source archives alone is insufficient.
The numerical certificates were checked before deletion and are not reclassified.

Final verification v1 passes 109 harness tests and 373 documentation pages, then
stops on the earlier 64 M report's source reference. Its full 960 CPU-second charge
is retained. Fresh verification v2 checks that exact historical reporting source
through its own reservation snapshot, without rewriting the report or repeating
scientific measurements. See [amendment 77](../specifications/SPEC-0046-amendment-77.md).

GPU_CONTROL_SETTLEMENT_PENDING

[Compact assessment/control results](lp-billion-gpu-control-results.json) and
[every exclusive timing phase](lp-billion-gpu-control-phases.csv) retain source,
resource, proof and memory bindings. Large evidence remains under
`/storage/ai-optimizer-billion-v1/gpu-control-64m-v1` and `gpu-control-1b-v1`.
'''
    p=ROOT/'docs/benchmarks/lp-billion.md';old=p.read_text()
    require('## GPU assessment and control with strict CPU acceptance' not in old,'fresh assessment/control report')
    p.write_text(old+text)
    handoff=f'''# Current agent handoff: GPU assessment/control measured (2026-11-22)

Opt-in image-v11 offloads exact-tree residuals, restart movement norms and original
primal feasibility. Original CPU dual/gap proofs remain exact, and every accepting
assessment rechecks original CPU feasibility. Strict original-model 1e-9 criteria,
public defaults, control100/certificate500 and original solve/prep/pack CUDA remain.
Native quality-v3, full diagnostic, sixty exact continuations, independent scalar
checks and all four complete sanitizers pass. Preserve all failures/full charges.

All twelve fresh 64 M cells and {available} new billion responses finish with
independent final/intermediate audits. The interrupted wide candidate remains
missing, with its full charge, original cleanup receipt and supplemental cleanup
proof. Only the four untouched cases resume after fresh operational admission. Before/after control / assessment / complete medians:
64 M {small['control_ratio_median']:.3f}x / {small['assessment_ratio_median']:.3f}x / {small['complete_ratio_median']:.3f}x;
billion {large['control_ratio_median']:.3f}x / {large['assessment_ratio_median']:.3f}x / {large['complete_ratio_median']:.3f}x.
Billion controls are historical v10; retain unequal work, deadlines, regressions
and uncertified endpoints. {large['jointly_certified_pairs']} historical pairs certify.
Broad FP4 certified superiority remains unestablished. Both cohorts are complete;
never rerun attempted cells or completed drivers.

Approved totals are 370000 CPU / 44000 GPU seconds; CPU phase caps are
10000/26000/58000/162000/113000/1000 and GPU 10000/34000. The immutable approval
chain includes recovery, both packing transfers and the assessment extension.
Operational CPU v29 / GPU v23 bind current resource sources. Four slots, 128 GiB
host, 80 GiB GPU, 400 GiB storage, headroom, idle/ownership checks and all advisories
remain unchanged. Container-only; no reset, host escape, other-job signal or owner
inference. Earlier general allocation remains unchanged. Commit locally only.

At the user's explicit request, obsolete large data is deleted after audits;
{released:.3f} GiB is released including verified source compaction. New snapshots
share immutable source objects. Keep all small results and failures. Historical
raw-data replay requires regeneration; no full portable replay is claimed.

Final verification v1 retains a 960 CPU-second failure on a historical report
source reference. Verification v2 uses the exact retained source from the original
64 M reporting reservation; no scientific measurement repeats. See
[amendment 77](docs/specifications/SPEC-0046-amendment-77.md).

GPU_CONTROL_SETTLEMENT_PENDING

Report: [GPU assessment/control](docs/benchmarks/lp-billion.md#gpu-assessment-and-control-with-strict-cpu-acceptance).
Results: [compact evidence](docs/benchmarks/lp-billion-gpu-control-results.json).

'''
    for name in ['AGENTS.md','state/active-task.md']:
        p=ROOT/name;prefix=handoff.replace('(docs/','(../docs/') if name.startswith('state/') else handoff
        p.write_text(prefix+p.read_text())
    print('assessment/control narrative written',flush=True)
if __name__=='__main__':main()
