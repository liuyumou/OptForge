"""Render the completed billion cohort without omitting limits or refusals."""
from lp_billion_common import BASE,ROOT,load,resolve,require


def main():
    report=load(ROOT/'docs/benchmarks/lp-billion-full-results.json')
    rows=report['cells'];extra=report['supplemental']['cells']
    ours=[r for r in rows if r.get('response')]
    supported=[r for r in extra if r.get('response')]
    capacity=load(BASE/'copt-nopresolve-capacity-v1.json')
    number=lambda value:f'{value/1e9:.3f}'
    project_table=['| Family | Lane | Accepted updates | Outcome | Solver preparation (s) | Complete cost (s) | Solver peak RSS (GiB) |',
                   '| --- | --- | ---: | --- | ---: | ---: | ---: |']
    for r in ours:
        project_table.append(f"| {r['family']} | {r['lane']} | {r['logical']} | {r['status']} | {number(r['solver_preparation_ns'])} | {number(r['complete_ns'])} | {r['solver_child_hwm_bytes']/2**30:.3f} |")
    copt_table=['| Family | Outcome | PDLP iterations | Strict certificate | Complete cost (s) | Solver peak RSS (GiB) |',
                '| --- | --- | ---: | --- | ---: | ---: |']
    for r in extra:
        if r['status']=='unsupported_capacity':
            copt_table.append(f"| {r['family']} | Unsupported: {'; '.join(r['capacity']['reasons'])} | — | No | — | — |")
        elif 'response' not in r:
            peak=r.get('solver_child_hwm_bytes')
            peak_text=f'{peak/2**30:.3f} (partial)' if peak is not None else 'Missing'
            copt_table.append(f"| {r['family']} | Attempted; missing response | — | No | Excluded | {peak_text} |")
        else:
            status={1:'Optimal status',8:'Time limit'}.get(r['status'],str(r['status']))
            if not r.get('has_solution'):status+='; no endpoint'
            total=number(r['complete_ns']) if r.get('timing_eligible') else 'Excluded'
            copt_table.append(f"| {r['family']} | {status} | {r['native']['PDLPIter']} | {'Yes' if r['certified'] else 'No'} | {total} | {r['solver_child_hwm_bytes']/2**30:.3f} |")
    coupled={r['lane']:r for r in ours if r['family']=='coupled_blocks'}
    phase_keys=[('Original input and transpose',['input_hash_validation']),
                ('GPU-backed preparation engine',['preparation_engine']),
                ('Operator and initial control',['preparation_operator','preparation_control']),
                ('FP4 packing',['preparation_packing']),('Device setup',['device_setup']),
                ('Device advance',['device_advance']),('Original-model control',['original_model_control']),
                ('Restart/weight control',['restart_weight_control']),('Internal strict certification',['strict_certificate']),
                ('Cold independent final proof',['independent_final_check'])]
    phase_table=['| Exclusive phase | GPU FP64/native (s) | FP32 (s) | FP4x2 (s) |','| --- | ---: | ---: | ---: |']
    included=set()
    for title,keys in phase_keys:
        included.update(keys)
        values=[sum(coupled[l]['complete_cost_ledger']['exclusive_ns'][k] for k in keys) for l in ['native','fp32','fp4x2']]
        phase_table.append('| '+title+' | '+' | '.join(number(v) for v in values)+' |')
    other=[sum(v for k,v in coupled[l]['complete_cost_ledger']['exclusive_ns'].items() if k not in included) for l in ['native','fp32','fp4x2']]
    phase_table.append('| All other measured phases | '+' | '.join(number(v) for v in other)+' |')
    phase_table.append('| **Complete cost** | '+' | '.join('**'+number(coupled[l]['complete_ns'])+'**' for l in ['native','fp32','fp4x2'])+' |')
    new_count=sum(r['status']!='unsupported_capacity' for r in extra);new_responses=len(supported);new_cert=sum(r.get('certified',False) for r in supported)
    peak_low=min(r['solver_child_hwm_bytes'] for r in ours)/2**30
    peak_high=max(r['solver_child_hwm_bytes'] for r in ours)/2**30
    body='''## Approved recovery and billion execution

The approved continuation is complete. All eighteen supported project runs on six
connected LPs with **one billion original matrix nonzeros each** return results,
and every final/intermediate assessment passes independent agreement checking.
Three runs certify: all three tall-family lanes. The other fifteen retain their
update-limit or deadline outcomes. The original twelve default-COPT billion slots
remain unsupported. A separate COPT GPU PDLP configuration with Presolve=0 attempts
NEW_COUNT supported billion runs and returns NEW_RESPONSES responses; NEW_CERT pass the same strict certificate.
All six slots of that supplemental roster remain visible below.

The user's explicit approval and [amendment 44](../specifications/SPEC-0046-amendment-44.md)
authorize cumulative 320000 CPU / 35000 GPU seconds and recovery of only the exact
recorded overrun. Fresh operational CPU v20 passes 75 supervisor / 59 resource
tests; a six-minute idle window and GPU v17's sixty exact continuations pass.
The failed stale-allocation CPU v19 test retains its full 720 CPU-second charge.
The original COPT overrun and all other failed reservations retain their full
charges and sources. No attempted scientific cell repeats. Four CPU slots,
128 GiB sampled aggregate host RSS, 80 GiB owned device buffers, 400 GiB owned
storage, physical headroom and every idle/ownership guard remain unchanged.
All work and read-only ownership inspection remain inside the container.

The [full-run protocol](../specifications/SPEC-0046-amendment-46.md) prospectively
selects 1000 updates as the largest common 500-update increment fitting all
supported solve, strict final/intermediate audit and endpoint/repaired-witness
storage reservations. Control100/certificate500 and normalized original-model
1e-9 criteria stay exact. The requested solver allowance is 600 seconds after
original loading; mandatory final checks and opaque vendor calls can overshoot.
Actual elapsed costs, including overshoots, appear below. A valid proof arriving
after a deadline never regrades that outcome as a certified solve.

### Full project results

`native` means GPU FP64. Every lane uses admitted image-v9 GPU preparation.
Solver preparation below sums engine, operator, packing and initial control;
it excludes original input/transpose and device setup, which are separate phases.
Complete cost includes the fresh process and a cold independent final proof.
Additional distinct intermediate proofs are retained as offline audit cost.

PROJECT_TABLE

Only coupled_blocks performs actual FP4 arithmetic: 75% of accepted product work.
The other FP4x2 requests select FP32 because they have no eligible canonical tiles.
Wide native/FP32 accept 700 updates after 800 physical attempts; wide FP4x2 accepts
500 after 600 physical attempts. Those deadline comparisons have different work
and cannot be described as equal-work speedups. All returned endpoint checks,
including rejected and deadline endpoints, remain in the compact evidence.

### Where the coupled solve spends its time

All three coupled runs accept 1000 updates and remain uncertified. Their complete
exclusive phase accounting is:

PHASE_TABLE

FP4 device advancement is 4.85x faster than GPU FP64 and 3.93x faster than FP32.
However, packing costs 74.794 seconds, exceeding the 23.937 seconds saved against
FP32 advancement. Complete FP4 cost is 511.561 seconds versus 461.850 for FP32
and 502.028 for GPU FP64. Thus this run does **not** establish a total-solve FP4
benefit. Input timing also varies: 108.633 / 64.196 / 64.286 seconds for native,
FP32 and FP4; these are fresh processes without flushed caches, with one rotated
repetition. No broad repeatable superiority is claimed.

The FP4 preparation engine itself is 23.010 seconds. Its nested GPU telemetry
records 0.429 seconds of scaling, 0.680 of spectral products, 5.632 of setup and
10.901 of download. These are subintervals, not extra costs to add to the table;
remaining engine work is included in its total. Twenty power iterations remain.
Zero-eligible FP4 requests also incur packing: irregular 74.153 seconds, wide
78.331 and tall 67.921. Avoiding that unnecessary packing and reducing actual
FP4 packing, original-model control and repeated assessment are measured next
targets; no unvalidated numerical change is adopted in this completed cohort.

`input_hash_validation` includes chunk reading/hashing/decoding, canonical
validation **and original CSR-to-CSC construction**. It is not pure disk I/O.
Device advancement is wall time around GPU work, not kernel-active time. All
exclusive phases, including checkpointing, uploads/downloads, witness output,
teardown and process/response overhead, are in the [phase CSV](lp-billion-full-phases.csv).
The [compact JSON](lp-billion-full-results.json) retains nested preparation
telemetry, physical/accepted work, proofs, capacity refusals and comparisons.

### Installed COPT comparison

The original automatic-presolve COPT CPU-auto and GPU-PDLP baseline remains
capacity-unsupported in all twelve billion slots. Its completed capacity responses
have zero optimization iterations; three 256 M cells and one 512 M cell retain
owned-child interruptions. The nine never-started 64 M tail cells complete.
Setup-only responses cannot establish full optimization workspace, and several
memory forecasts exceed the admitted limits. These are capacity dispositions,
not measured billion-scale timings or evidence that project solves beat COPT.
See [amendment 48](../specifications/SPEC-0046-amendment-48.md).

The separately identified [Presolve=0 variant](../specifications/SPEC-0046-amendment-49.md)
uses the same installed COPT 8.0.6 in `/root/copt80`, four threads, GPU PDLP,
MatrixTol=0, FeasTol=DualTol=1e-9, PDLPTol=1e-12 and no crossover. Its unchanged
48000 MB vendor memory setting is soft; measured process and device memory guards
remain authoritative. Nine contracts and twelve small admission cases pass,
including eight independently certified optima. It then attempts all ten frozen
64/256/512 M capacity cells before freezing its separate six-slot billion roster.
Every smaller observed path must demonstrate optimization workspace and fit the
prospective growth/headroom forecast. Missing, interrupted and setup-only paths
remain disqualifying; forecasts are empirical, not hard bounds on vendor internals.

COPT_TABLE

The tall COPT attempt stops without a response or a retained process HWM. Its
original settlement records cleanup_incomplete with no overrun and retains the full
3600 CPU / 900 GPU-second charge. Subsequent exact PID/start-time checks prove all
four owned identities gone; the GPU returns to the idle baseline. [Amendment 50](../specifications/SPEC-0046-amendment-50.md)
uses the existing non-overrun cleanup/readmission path, fresh CPU v21, a complete
idle window and GPU v18 before the two untouched cells. It does not retry tall or
change its failure. The original guardian receipt overwrites the preceding stop
trigger, so the underlying cause is unresolved. Partial sampled memory cannot
serve as a completed optimizer-workspace measurement. Ill-scaled and degenerate
both reach their owned-child cutoffs without responses. Each retains the full
3600 CPU / 900 GPU seconds and settles with empty cleanup and no overrun. Failed attempts have no complete-cost
timing or recovered phase profile. The CSV retains observed child/reservation
durations where available and marks interrupted process memory as partial.

COPT's iteration count is not directly comparable with project updates. The
same requested 600-second solver allowance and original-model certificate criteria
apply, but project runs also have the common 1000-update ceiling. A time limit
without an endpoint has no independent final-proof cost and cannot establish a
certified-solve speedup. Vendor internal preprocessing and execution are opaque;
the CSV separates measurable input, adapter CSC/import, the vendor call, extraction,
teardown and final checking. Adapter preparation is not all vendor preparation.

### Memory, validation and retention

Project solver process peaks range from PEAK_LOW to PEAK_HIGH GiB. These kernel-
recorded process HWMs differ from the sampled aggregate owned-process peak, which
includes coordination, and from the separately measured independent audit peak.
All three measures and the sampled owned GPU peak appear in the phase CSV.
Memory limits and strict checks were preserved; the bounded representation now
permits these full billion-nonzero runs. This cohort has no paired old-image
billion solve, so it does not establish a before/after billion-scale memory or
GPU-preparation speedup. Earlier paired preparation results retain their own scope.

Image-v9's 66 bitwise preparation comparisons, sixty exact solve continuations,
all four complete sanitizers, and bounded-copy diagnostic remain applicable.
Numerical Rust/CUDA, both CUDA binaries, all 300 numerical source bindings and
public defaults stay exact. Full-run contract tests and three real strict-checker
replays admit the deadline-aware independent auditor. Final harness, documentation,
source-binding and owned-process verification are recorded in the final checkpoint.
The prior portable catalog remains unchanged; no new full portable replay is claimed.

Large evidence remains local under `/storage/ai-optimizer-billion-v1`, including
`full-billion-v1/freeze.json`, `copt-nopresolve-1b-v1/freeze.json`, complete raw
responses and strict final/intermediate audits. All failures, missing responses,
unsupported slots and regressions remain visible. The approved allocation stays
open, and the earlier general allocation stays unchanged. Local commit only;
no public adoption, confirmation or publication is released.
'''
    for old,new in [('NEW_COUNT',str(new_count)),('NEW_RESPONSES',str(new_responses)),('NEW_CERT',str(new_cert)),('PROJECT_TABLE','\n'.join(project_table)),('PHASE_TABLE','\n'.join(phase_table)),('COPT_TABLE','\n'.join(copt_table)),('PEAK_LOW',f'{peak_low:.3f}'),('PEAK_HIGH',f'{peak_high:.3f}')]:body=body.replace(old,new)
    path=ROOT/'docs/benchmarks/lp-billion.md';text=path.read_text()
    before=text.split('## Approved recovery and billion execution\n',1)[0]
    title,rest=before.split('## Scope and implementation\n',1)
    title=f'''# Billion-nonzero LP development on the Pro6000

The authorized billion-nonzero comparison is complete: eighteen project runs and
{new_count} supported COPT GPU attempts ({new_responses} returned responses), preserving strict original-model 1e-9 checking.
Three project runs and {new_cert} COPT runs certify; all limits and capacity refusals
remain visible. FP4 accelerates coupled device advancement but does not reduce
its complete cost. See [full results](#approved-recovery-and-billion-execution),
[phase timings](lp-billion-full-phases.csv) and [compact evidence](lp-billion-full-results.json).
Updated 2026-11-21 under [SPEC-0046](../specifications/SPEC-0046-billion-lp.md).
Historical checkpoints below retain their original scope and failures.

'''
    path.write_text(title+'## Scope and implementation\n'+rest+body)
    with path.open('a') as stream:stream.write('\nFULL_BILLION_SETTLEMENT_PENDING\n')
    handoff=f"""The approved continuation completes all eighteen project billion-NNZ runs and
{new_count} separately admitted COPT Presolve=0 GPU attempts ({new_responses} responses).
Project lanes certify 3/18, all tall; the separate COPT lane certifies {new_cert}/{new_count}.
Every returned final/intermediate assessment receives strict original-model 1e-9
independent checking. All six families and every lane slot remain visible: twelve
original default-COPT billion slots and three separate-variant slots are unsupported.
No attempted scientific cell repeats; both continuation sequences are complete.

The common project ceiling is 1000 updates with a requested 600-second solver
allowance, control100/certificate500 and full solve/audit/storage reservations.
All original Rust/CUDA, 300 numerical bindings and public defaults stay exact.
Image-v9 retains 66 bitwise preparation comparisons, sixty exact continuations,
all four complete sanitizers and the real chunk-copy diagnostic. A strict proof
after a deadline does not regrade the deadline as a certified solve.

Coupled performs 75% accepted FP4 work. GPU advancement takes 8.182 seconds versus
39.700 native GPU FP64 and 32.119 FP32, but complete FP4 cost is 511.561 seconds
versus 502.028 / 461.850. Packing costs 74.794 seconds, exceeding the 23.937-second
advancement saving against FP32. Zero-eligible FP4 requests still incur 68–78 seconds
of packing before FP32 fallback. Broad FP4 total-solve superiority is unestablished.
All exclusive phases and separate cold final/offline intermediate proofs are saved.
Input includes original CSR-to-CSC construction; advancement is not kernel-active
GPU time. One rotated repetition and unflushed caches limit timing interpretation.
Project process HWM ranges {peak_low:.3f}–{peak_high:.3f} GiB; sampled aggregate and audit
peaks are distinct. No paired before/after billion memory comparison is claimed.

The COPT tall interruption retains its missing response, cleanup=false settlement
and full 3600 CPU / 900 GPU charge. Four exact owned identities are subsequently
gone. Amendment 50 uses the existing non-overrun cleanup-disposition path and
fresh CPU v21 / five-minute idle window / GPU v18 before the two untouched cases.
Never retry tall; the preceding stop trigger was overwritten and remains unknown.

The user explicitly approved 320000 CPU / 35000 GPU seconds and recovery of the
single immutable original COPT overrun. Every failure and full charge remains.
No other overrun is exempted. Four CPU slots, 128 GiB aggregate host, 80 GiB owned
GPU and 400 GiB storage caps remain; all ownership, idle and physical headroom
guards remain. Container-only: no host escape, reset, shared-memory clearing,
other-job signals or owner inference. The earlier general allocation is unchanged.
The allocation stays open; commit locally only, no public adoption/publication.
No fresh full portable replay is claimed. Large evidence remains under
/storage/ai-optimizer-billion-v1, including full-billion-settled-checkpoint-v1.json.

FULL_BILLION_SETTLEMENT_PENDING
"""
    agent=ROOT/'AGENTS.md';prior=agent.read_text()
    marker='# Current agent handoff: GPU admission complete; COPT overrun closes execution (2026-11-21)'
    require(marker in prior,'preserve historical handoffs')
    links='\nReport: [full billion comparison](docs/benchmarks/lp-billion.md#approved-recovery-and-billion-execution).\nTimings: [phase CSV](docs/benchmarks/lp-billion-full-phases.csv).\nEvidence: [compact results](docs/benchmarks/lp-billion-full-results.json).\n\n'
    agent.write_text('# Current agent handoff: billion comparison complete (2026-11-21)\n\n'+handoff+links+marker+prior.split(marker,1)[1])
    state=ROOT/'state/active-task.md';prior=state.read_text();require(prior.startswith('# Active Task\n\n'),'active task heading')
    state.write_text('# Active Task\n\n## Billion comparison complete (2026-11-21)\n\n'+handoff+links.replace('](docs/','](../docs/')+prior.removeprefix('# Active Task\n\n'))
    print(dict(project=len(ours),copt=new_count,project_certified=3,copt_certified=new_cert),flush=True)

if __name__=='__main__':main()
