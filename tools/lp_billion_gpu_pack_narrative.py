"""Write the measured GPU packing report and local handoff without changing history."""
import statistics
from lp_billion_common import BASE,ROOT,load,ref,put,require

def main():
    data=load(ROOT/'docs/benchmarks/lp-billion-gpu-packing-results.json')
    small,large=data['cohorts'];require(small['scale']=='64m' and large['scale']=='1b','both complete packing cohorts')
    def table(report):
        rows=report['cells']+report['historical_controls'];lines=['| Family | Packing before / after (s) | Preparation before / after (s) | Complete before / after (s) | Updates before / after | Certified before / after |','| --- | ---: | ---: | ---: | ---: | --- |']
        for pair in report['comparisons']:
            a=next(r for r in rows if r['id']==pair['baseline']);b=next(r for r in rows if r['id']==pair['candidate'])
            if not pair['both_timing_eligible']:
                lines.append(f"| {pair['family']} | unavailable | unavailable | unavailable | {a.get('logical')} / {b.get('logical')} | {a.get('certified',False)} / {b.get('certified',False)} |")
                continue
            sec=lambda x:x/1e9
            lines.append(f"| {pair['family']} | {sec(a['preparation_detail_ns']['packing']):.3f} / {sec(b['preparation_detail_ns']['packing']):.3f} | {sec(a['solver_preparation_ns']):.3f} / {sec(b['solver_preparation_ns']):.3f} | {sec(a['complete_ns']):.3f} / {sec(b['complete_ns']):.3f} | {a['logical']} / {b['logical']} | {a['certified']} / {b['certified']} |")
        return '\n'.join(lines)
    admission=load(BASE/'gpu-pack-gpu-v1/result.json');quality=load(BASE/'gpu-pack-quality-v7/result.json')
    memory=['| Billion family | Solver peak host RSS before / after (GiB) | Sampled aggregate host RSS after (GiB) | Sampled owned GPU peak after (GiB) |','| --- | ---: | ---: | ---: |']
    all_large=large['cells']+large['historical_controls']
    equal=[p for p in large['comparisons'] if p['both_timing_eligible'] and p.get('same_accepted_updates')]
    equal_summary='No equal-update historical pair has an eligible complete timing.'
    if equal:
        equal_summary=(f"The {len(equal)} equal-update historical pairs have descriptive preparation / complete-cost median ratios of "
            f"{statistics.median(p['preparation_ratio'] for p in equal):.3f}x / {statistics.median(p['complete_ratio'] for p in equal):.3f}x. "
            f"{sum(p.get('exact_numerical_transcript',False) for p in equal)} retain exact full numerical transcripts. "
            'Equal update counts do not by themselves establish certification or remove cross-run input/cache variability.')
    gib=lambda v:f'{v/2**30:.3f}' if v is not None else 'unavailable'
    for pair in large['comparisons']:
        a=next(r for r in all_large if r['id']==pair['baseline']);b=next(r for r in all_large if r['id']==pair['candidate'])
        memory.append(f"| {pair['family']} | {gib(a.get('solver_child_hwm_bytes'))} / {gib(b.get('solver_child_hwm_bytes'))} | {gib(b.get('sampled_aggregate_peak_rss_bytes'))} | {gib(b.get('sampled_peak_owned_device_bytes'))} |")
    coupled=next(r for r in large['cells'] if r['family']=='coupled_blocks')
    bottlenecks='The coupled case has no eligible complete timing.'
    if coupled.get('timing_eligible'):
        phases=sorted(coupled['complete_cost_ledger']['exclusive_ns'].items(),key=lambda p:p[1],reverse=True)
        bottlenecks=('The new billion coupled run accepts '+f"{100*coupled['accepted_fp4_share']:.1f}%"+' FP4 product work. '
            'Its largest complete-cost intervals are '+', '.join(f'`{name}` ({ns/1e9:.3f} s)' for name,ns in phases[:4])+'. '
            'These retained intervals identify the remaining costs after GPU packing.')
    text=f'''

## GPU FP4 packing and zero-eligible fast path

The opt-in image-v10 array executor moves structural eligibility counting,
coefficient-domain and exact transpose validation, residual extraction and normal
E2M1 encoding to a separate GPU module. It returns before allocating packing
fragments or residual arrays when no tile qualifies. The redundant CPU coefficient
scan is deferred to the GPU validator only for this opt-in path. Host work retains
sorted canonical metadata and offsets; a bounded structural-hash overflow explicitly
uses the exact CPU packer. Both matrix orientations retain identical packed bits.
The first implementation downloads canonical Packed and uses the unchanged device
initializer, so these transfers and context costs remain in measured total time.

Public defaults, the original FP64 preparation and solve CUDA modules, strict
original-model 1e-9 certification, control100/certificate500 and all resource guards
remain unchanged. The exact storage inventory now uses a source-bound native
counter to stay within the same supervision limit as the evidence tree grows;
it still traverses every file, deduplicates hardlinks and excludes symlinks and
directories. Independent recompilation, legacy-counter comparisons and fresh
CPU/GPU operational gates admit that resource change. CPU acceptance passes {quality['rust_tests']} isolated Rust tests,
formatting, Clippy, release and CUDA compilation. Device admission passes
{admission['packing']['bitwise_comparisons']} bitwise packing comparisons,
{admission['packing']['invalid_inputs_rejected']} malformed-input rejections,
{len(admission['rows'])} exact solve continuations and
{sum(len(r['serial']) for r in admission['rows'])} independent strict scalar checks.
All four complete sanitizers cover the packing suite and twenty solve continuations
each. The new exponent batches include subnormals, the exponent clamp and neighbors
of powers of two and six. Unchanged preparation kernels retain their prior complete
admission, including the original twenty deep-norm iterations.

The fresh six-family paired 64 M cohort uses 100 updates and rotated version order.
Its descriptive preparation / complete-cost median ratios are
{small['preparation_ratio_median']:.3f}x / {small['complete_ratio_median']:.3f}x.
All failed, regressing and uncertified outcomes remain in the compact results.

{table(small)}

The six new one-billion-original-nonzero solves use the retained 1000-update ceiling,
600-second requested solver allowance and strict independent final/intermediate
checks. Their image-v9 controls are historical runs: these are descriptive
comparisons across runs, with no randomized paired billion-trial claim. Deadline or
update-count differences remain explicit. The descriptive preparation / complete
median ratios are {large['preparation_ratio_median']:.3f}x /
{large['complete_ratio_median']:.3f}x, with {large['jointly_certified_pairs']} jointly
certified pairs. Uncertified bounded runs do not establish certified-solve speedup.

{table(large)}

{equal_summary}

{bottlenecks}

{chr(10).join(memory)}

Solver peak RSS comes from the dedicated child's high-water mark; aggregate host
and owned device peaks are sampled separately and are not added to that value.
The conservative pre-allocation bounds and physical host headroom remain enforced.

Complete cost includes the fresh solver process, response persistence and cold
independent final proof. Additional distinct intermediate proofs are reported as
separate offline audit costs. Input includes chunk reading, hashing, canonical
validation and original CSR-to-CSC construction. Every exclusive phase sums exactly
to complete cost; nested GPU packing metrics are not added a second time. GPU
advancement and packing metrics are host elapsed intervals, not kernel-active times.
Caches were not flushed. All family/lane limitations and actual FP4 work shares
remain visible; zero-eligible requests execute the established FP32 fallback.
Broad repeatable FP4 certified-solve superiority remains unestablished.

The allocation remains open at 320000 CPU / 35000 GPU seconds. Two explicit user
approvals transfer phase capacity within those totals. Retain every failed build,
CPU admission and sealing charge, and the excluded v6 source snapshot. The failed
seal's artifacts are admitted only by a separate read-only source/binary audit;
its original resource failure is unchanged. No attempted scientific cell repeats.
Container-only execution, idle/ownership checks, four CPU slots, 128 GiB host,
80 GiB owned GPU and 400 GiB storage caps remain unchanged. Commit locally only;
no public adoption, confirmation or fresh full portable replay is claimed.

GPU_PACKING_SETTLEMENT_PENDING

[Compact GPU packing results](lp-billion-gpu-packing-results.json) and
[all exclusive phase timings](lp-billion-gpu-packing-phases.csv) retain raw receipt,
source, proof and memory bindings. Large evidence stays under
`/storage/ai-optimizer-billion-v1/gpu-pack-64m-v1` and `gpu-pack-1b-v1`.
'''
    path=ROOT/'docs/benchmarks/lp-billion.md';prior=path.read_text();require('## GPU FP4 packing and zero-eligible fast path' not in prior,'fresh report section');path.write_text(prior+text)
    handoff=f'''# Current agent handoff: GPU FP4 packing measured (2026-11-21)

Opt-in image-v10 moves eligibility/validation/residual extraction/encoding to GPU,
skips packing allocations with no eligible tiles and preserves strict original-model
1e-9 checks, original preparation/solve CUDA, control100/certificate500 and defaults.
Native quality-v7 and separate read-only seal audit admit exact sources. All 81
bitwise packing comparisons, six malformed inputs, sixty exact continuations,
130 independent scalar checks and all four complete sanitizers pass. Retain all
failed admission/build/seal receipts and v6's non-admitted fixture snapshot.

Fresh six-family paired 64 M preparation / complete median ratios:
{small['preparation_ratio_median']:.3f}x / {small['complete_ratio_median']:.3f}x.
Six new billion FP4-request cells compare descriptively to retained v9 controls:
{large['preparation_ratio_median']:.3f}x / {large['complete_ratio_median']:.3f}x;
{large['jointly_certified_pairs']} jointly certified pairs. Every returned final and
intermediate assessment is independently audited. Preserve all outcomes and
unequal deadline/update work. Broad FP4 certified superiority is unestablished.
Both cohorts are complete; never rerun their attempted cells or completed drivers.

Approved totals remain 320000 CPU / 35000 GPU seconds. CPU phase caps are
8000/22000/52000/140000/97000/1000; GPU admission7000/development28000.
Preserve original recovery and both explicit transfer approvals. All failed
charges remain. Resource readmission CPU v26 / GPU v21 binds the exact native
storage counter, with the legacy Python walk retained as an independent oracle.
Four slots, 128 GiB host, 80 GiB GPU, 400 GiB storage, physical
headroom, one-second supervision and all 100 ms advisories remain unchanged.
Container-only, idle-only; no reset, host escape, other-job signal or owner inference.
Earlier general allocation remains unchanged. Commit locally only; no publication.

GPU_PACKING_SETTLEMENT_PENDING

Report: [GPU packing](docs/benchmarks/lp-billion.md#gpu-fp4-packing-and-zero-eligible-fast-path).
Results: [compact evidence](docs/benchmarks/lp-billion-gpu-packing-results.json).

'''
    p=ROOT/'AGENTS.md';p.write_text(handoff+p.read_text());p=ROOT/'state/active-task.md';p.write_text(handoff+p.read_text())
    put(BASE/'gpu-pack-narrative-v1.json',dict(status='written_with_pending_settlement',report_pending_path=str(path.relative_to(ROOT)),source=ref(__file__)))
if __name__=='__main__':main()
