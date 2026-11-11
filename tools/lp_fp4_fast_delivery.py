"""Verify and publish the complete FP4 optimization evidence, without reruns."""
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import statistics as st
import subprocess
from lp_fp4_fast_common import ROOT, BASE, CPU_CAPS, GPU_CAPS, load, put, ref, checked, require
from lp_fp4_fast_budget import accounting
from lp_fp4_fast_study import STUDY, cells
from lp_fp4_gpu_delivery_v3 import verify_manifest

DEST=ROOT/'docs/benchmarks/data'
REPORT=ROOT/'docs/benchmarks/lp-fp4-fast.md'


def resources():
    cpu,gpu=accounting();rows=[]
    for p in sorted((BASE/'resources').glob('*.reservation.json')):
        settled=p.with_name(p.name.replace('.reservation.json','.settlement.json'))
        receipt=p.with_name(p.name.replace('.reservation.json','.resource.json'))
        item=load(settled) if settled.exists() else load(p)
        clean=None
        if receipt.exists():
            r=load(receipt);clean=r.get('guardian_cleanup',{}).get('empty') and r.get('result',{}).get('cleanup',{}).get('empty')
            require(clean,'nonempty supervisor cleanup: '+str(p))
        rows.append(dict(reservation=ref(p),settlement=ref(settled) if settled.exists() else None,charged=item,cleanup_empty=clean))
    require(all(cpu[k]<=v*10**9 for k,v in CPU_CAPS.items()),'CPU cap')
    require(all(gpu[k]<=v*10**9 for k,v in GPU_CAPS.items()),'GPU cap')
    return dict(cpu_ns=cpu,gpu_ns=gpu,total_cpu_ns=sum(cpu.values()),total_gpu_ns=sum(gpu.values()),cpu_caps_seconds=CPU_CAPS,gpu_caps_seconds=GPU_CAPS,resources=rows)


def bridge():
    index={};resolved=[]
    for path in (BASE/'sources').glob('*/manifest.json'):
        for item in load(path)['sources']:index.setdefault(item['sha256'],item)
    for row in load(BASE/'executor-archive/receipt.json')['rows']:
        index[row['executable']['sha256']]=row['executable']
    for path in sorted(BASE.glob('build-*/fast.cu')):
        item=ref(path);index[item['sha256']]=item
    for path in sorted(BASE.glob('*/manifest.json')):
        if path.parent.name.startswith(('study-','sources','executor-archive')):continue
        m=load(path)
        for key in ('binary','driver','image'):
            if key not in m:continue
            original=m[key];current=ROOT/original['path']
            if current.exists() and hashlib.sha256(current.read_bytes()).hexdigest()==original['sha256']:
                checked(original);continue
            archived=index.get(original['sha256']);require(archived is not None,'missing preserved bytes: '+str(original))
            checked(archived);resolved.append(dict(manifest=ref(path),field=key,original=original,exact_archived_bytes=archived))
    return dict(status='passed',rows=resolved,executor_archive=ref(BASE/'executor-archive/receipt.json'),scientific_reexecution=False)


def summaries(rows):
    groups=defaultdict(list)
    for r in rows:groups[(r['family'],r['blocks'],r['format'],r['components'],r['backend'])].append(r)
    out=[]
    for key,group in sorted(groups.items()):
        require({r['repetition'] for r in group}=={0,1,2},'cold repetition coverage')
        cuda=[st.median(s['cuda_ms'] for s in r['samples']) for r in group]
        prepared=[st.median(s['prepared_ns'] for s in r['samples']) for r in group]
        cold=[r['cold_input_to_export_ns'] for r in group]
        out.append(dict(family=key[0],blocks=key[1],format=key[2],components=key[3],backend=key[4],
            cuda_median_ms=st.median(cuda),cuda_process_median_range_ms=[min(cuda),max(cuda)],
            prepared_median_ns=st.median(prepared),prepared_process_median_range_ns=[min(prepared),max(prepared)],
            cold_batch_median_ns=st.median(cold),cold_batch_range_ns=[min(cold),max(cold)],
            preparation_median_ns=st.median(r['preparation_ns'] for r in group),
            serialization_median_ns=st.median(r['serialization_ns'] for r in group),
            error=max(r['observed_error'] for r in group),primal_residual=max(r['original_a_primal_residual'] for r in group),
            counts=group[0]['counts'],phases_median_ns={k:st.median(r['phases_ns'][k] for r in group) for k in group[0]['phases_ns']}))
    by_key={(s['family'],s['blocks'],s['format'],s['components'],s['backend']):s for s in out}
    for s in out:
        base=by_key[(s['family'],s['blocks'],s['format'],s['components'],'legacy')]
        native=min(by_key[(s['family'],s['blocks'],64,1,b)]['cuda_median_ms'] for b in ('legacy','native_cached'))
        s['kernel_speedup_vs_legacy']=base['cuda_median_ms']/s['cuda_median_ms']
        s['kernel_speedup_vs_faster_native_control']=native/s['cuda_median_ms']
        s['prepared_speedup_vs_legacy']=base['prepared_median_ns']/s['prepared_median_ns']
    return out


def write_report(result,host,failures):
    ss=result['summaries'];lookup={(s['family'],s['blocks'],s['format'],s['components'],s['backend']):s for s in ss}
    selected=[s for s in ss if s['format']==4 and s['backend']=='hardware']
    gains=[s['kernel_speedup_vs_legacy'] for s in selected]
    geomean=math.exp(st.mean(math.log(v) for v in gains))
    text=f'''# FP4 optimization: GPUP-FP4-FAST

The separate [SPEC-0028](../specifications/SPEC-0028-fp4-fast.md) /
[ADR-0060](../decisions/ADR-0060-fp4-fast.md) implementation completes all 288
frozen cold batch cells and 2016 fresh prepared windows. Every optimized endpoint
matches its lane's retained implementation in state, component codes, exponents
and update flags. FP4 CUDA time improves **{min(gains):.2f}–{max(gains):.2f}×**
across the 24 model-size/component combinations; their geometric mean is
**{geomean:.2f}×**. These are bounded inner-iteration measurements, not certified
LP solve times. No supported solver preset is selected.

## Measured performance

Each entry is the median of three process medians, each containing seven fresh
32-update windows. Times below are CUDA event microseconds, including any host
submission gap between the events. “Native ratio” uses
the faster of the retained and cached FP64 controls, so a number below one means
FP4 is still slower. Full samples and observed three-process ranges are in the
[machine result](data/fp4-fast-result-v1.json). Three cold repetitions do not
establish a universal speedup or a tight population confidence interval.

| Coefficients | Variables | FP4 components | Legacy µs | Optimized µs | Same-lane speedup | Native ratio | Iterate error |
|---|---:|---:|---:|---:|---:|---:|---:|
'''
    for family in ('dyadic','rich'):
        for blocks in (64,4096):
            for k in (2,4,8):
                s=lookup[(family,blocks,4,k,'hardware')];old=lookup[(family,blocks,4,k,'legacy')]
                text+=f"| {family} | {blocks*32} | {k} | {old['cuda_median_ms']*1000:.2f} | {s['cuda_median_ms']*1000:.2f} | {s['kernel_speedup_vs_legacy']:.2f}× | {s['kernel_speedup_vs_faster_native_control']:.2f}× | {s['error']:.3g} |\n"
    text+='''
The rich family has binary64 coefficients that keep the later matrix components
active. Its inclusion prevents the zero-plane optimization from being evaluated
only on the pilot's exactly dyadic matrices. Both families consist of independent
32-by-32 blocks; this is not a coupled sparse LP benchmark. Iterate error compares
against an independent original-A FP64 recurrence. The nonzero primal residuals
remain reported; neither quantity is a final certificate.

Prepared wall time includes a fresh device checkpoint reset, export and an
original-A residual observation. Cold input-to-export time covers preparation,
binary serialization and process delivery of **seven windows**, rather than a
single solve. Independent reference construction/check costs are reported
separately. Context creation, export/checking and model delivery can dominate
these short windows, so the kernel ratios must not be presented as cold solver
speedups. The worker reuses immutable model preparation and its CUDA context
across fresh windows; it retains complete checkpoint/cancellation semantics.

## What changed and why

- Replaced the linear scale search with exponent extraction and a bounded test.
  Native warp reductions replace the five-stage maximum shuffle tree.
- Used native E2M1 conversion, preserving the low FP32 component's rounding
  decision at every midpoint; simplified exact component subtraction and packing.
- Skipped exact-zero matrix planes, prepared matrix fragments once, and used
  MMA columns for different components of the same RHS. An eight-component
  vector now uses all eight columns instead of discarding seven.
- Added aligned vector loads. Retained and diagnosed a CUDA 13 FP16 extraction
  failure: generated PTX read 32 bits at `base + 2*lane`. The first volatile-word
  workaround failed; an explicit 16-bit shared-memory load passed admission.
- Vectorized host preparation while preserving the rational oracle's codes and
  scales; replaced large JSON arrays with bounded lossless binary transport.
- Reused event objects and restored prepared checkpoints on the device. Fresh
  prepared windows have zero host checkpoint-copy bytes. Full exports and
  original-A observations remain charged.

Shared and register matrix-cache variants remain recorded. They are not uniformly
faster: the eight-component register cache increased register pressure and lost
performance. The cached FP64 control is also not uniformly faster. The final
comparison retains both native controls and matched optimized FP8/FP16 controls.
FP16 remains an important alternative when its arithmetic/quality contract fits.

## Bottleneck evidence

The original slowdown was predominantly representation/encoding and work
organization. It was not a PCIe transfer in every persistent update: the original
persistent window already had one launch and no per-update host copies.
The completed ablations isolate scale/encoding, zero products, matrix packing,
column utilization, caching and the final hardware-encoding step.

Device-clock instrumentation of the intermediate candidate attributed roughly
70–73% of small-workload cycles to reconstruction, projection and re-encoding;
the rest was mostly the two component products. Instrumentation changes the
compiled kernel and adds clock instructions, so these are scoped phase
observations, not hardware-stall percentages for the final image. Nsight Compute
refused counter access with `ERR_NVGPUCTRPERM`; that failure is retained. No host
security setting or driver was changed.

The original 1–64-warp workloads underfilled this GPU. Larger workloads improve
throughput utilization, while single-RHS Tensor arithmetic and component
normalization still impose limits. FP4 hardware throughput does not automatically
translate to solver throughput. The final timing table shows both wins and
remaining losses against native arithmetic.

## Host preparation

Fresh-cache measurements reproduce exactly the original prepared requests for
64 blocks. These timings cover host preparation only, separately from GPU and
context costs. The [host receipt](data/fp4-fast-host-preparation-v1.json) retains
all three repetitions and both implementations.

| Lane | Rational preparation ms | Vectorized preparation ms | Speedup |
|---|---:|---:|---:|
'''
    for f,k in ((64,1),(8,4),(16,2),(4,2),(4,4),(4,8)):
        rr=[r for r in host['rows'] if r['format']==f and r['components']==k]
        old=st.median(r['rational_ns'] for r in rr);new=st.median(r['vectorized_ns'] for r in rr)
        text+=f'| FP{f} ×{k} | {old/1e6:.3f} | {new/1e6:.3f} | {old/new:.1f}× |\n'
    text+='''
## Acceptance and retained history

Acceptance includes 60 independent rational product cases, 72 rich-trajectory /
midpoint comparisons, 42 execution/rollback cases, and 24 paths under each of
memcheck, racecheck, initcheck and synccheck. Sanitizer requests include two fresh
windows and therefore exercise device checkpoint restoration. All four report
zero errors; racecheck also reports zero warnings.

The full repository gate passes 638 Rust tests, 593 Python tests, replay,
dependency/artifact checks, documentation and smoke. The updated isolated runtime
passes four Rust tests and Clippy; seven focused Python tests cover the final
preparation, transport and reference paths. The complete software/device evidence
is in the [acceptance record](data/fp4-fast-acceptance-v1.json).

The completed pilot's three manifests and original sources/results remain exact.
Development source snapshots, images, partial outputs and failures remain
versioned. Four earlier executors were reconstructed byte-for-byte from frozen
sources and archived, without rerunning scientific cells; the explicit archive
bridge preserves their original hashes. The [evidence record](data/fp4-fast-evidence-v1.json)
contains that bridge, compiler/device identities and all retained failures.

| Retained failed attempt | Charged CPU seconds | Charged GPU seconds |
|---|---:|---:|
'''
    for row in failures:
        name=Path(row['reservation']['path']).name.removesuffix('.reservation.json');c=row['charged']
        text+=f"| {name} | {c['cpu_ns']/1e9:.3f} | {c['gpu_ns']/1e9:.3f} |\n"
    text+='''
The independent ceiling is 128000 CPU / 18000 GPU seconds, with all failed
reservations retained. [Accounting](data/fp4-fast-accounting-v1.json) reports
phase totals and every reservation/settlement; the active reporting reservation
is conservatively charged in full until final cleanup settles. Historical funds
remain closed and were not reused. No frozen timing cell was retried.

Certified integration still requires the recovery-policy contract, nontrivial
long trajectories, original-model audits and independent final 1e-7/1e-9 checking.
The old FP4-PROTO and GPUP-8 remain incomplete and GPUP-9 remains gated. Delivery
is a local commit only; no push or publication.
'''
    REPORT.write_text(text)


def main():
    for version in (1,2,3):verify_manifest(ROOT/f'artifacts/gpup-fp4-gpu-pilot-v{version}/manifest.json')
    changed=subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True).splitlines()
    require(set(changed)<={'AGENTS.md','state/active-task.md','state/backlog.yaml','docs/plans/gpu-lp-precision-roadmap.md'},'historical tracked files changed')
    m=load(STUDY/'manifest.json')
    for item in m['sources']+[m['binary'],m['image'],m['build'],m['admission'],m['grid_cpu'],m['inventory']]:checked(item)
    study=load(STUDY/'result.json');rows=study['rows']
    require(study['status']=='passed' and len(rows)==288 and {r['id'] for r in rows}=={r['id'] for r in cells()},'complete frozen grid required')
    endpoints={}
    for r in rows:
        for key in ('input','output','stdout','stderr'):checked(r[key])
        require(len(r['samples'])==7 and r['returncode']==0 and r['counts']['iteration_launches']==1 and r['counts']['iteration_copies']==0 and r['counts']['prepared_reset_host_copy_bytes']==0,'window/work coverage')
        key=(r['family'],r['blocks'],r['format'],r['components'])
        require(key not in endpoints or endpoints[key]==r['endpoint_sha256'],'matched endpoint hash')
        endpoints[key]=r['endpoint_sha256']
    ss=summaries(rows);archive=bridge();account=resources()
    failures=[r for r in account['resources'] if r['charged'].get('status')=='refused']
    host=load(BASE/'host-preparation.json')
    result=dict(kind='fp4-fast-result-v1',status='complete_empirical_optimization',completed_cells=288,planned_cells=288,fresh_windows=2016,certified=False,selected_solver_preset=None,manifest=ref(STUDY/'manifest.json'),rows=rows,summaries=ss)
    put(DEST/'fp4-fast-result-v1.json',result)
    put(DEST/'fp4-fast-host-preparation-v1.json',host)
    put(DEST/'fp4-fast-accounting-v1.json',account)
    put(DEST/'fp4-fast-acceptance-v1.json',dict(status='passed',admission=load(BASE/'admission-v8/result.json'),software={name:load(BASE/'resources'/(name+'.settlement.json')) for name in ('native-gate-v1','cpu-build-v6','grid-cpu-v1')},study=ref(STUDY/'result.json'),matched_endpoints=len(endpoints),fresh_windows=2016))
    put(DEST/'fp4-fast-evidence-v1.json',dict(manifest=m,compiler=load(BASE/'build-v8/receipt.json'),inventory=load(STUDY/'inventory.json'),archive_bridge=archive,failures=failures,exploratory={p.parent.name:ref(p) for p in sorted(BASE.glob('*/result.json')) if not p.parent.name.startswith('study')},counter_refusal=ref(BASE/'counters-v1/attempt.json'),prior_pilot=ref(ROOT/'docs/benchmarks/data/fp4-gpu-pilot-result-v3.json')))
    write_report(result,host,failures)
    print(json.dumps(dict(status=result['status'],cells=288,windows=2016,cpu_seconds=account['total_cpu_ns']/1e9,gpu_seconds=account['total_gpu_ns']/1e9)))

if __name__=='__main__':main()
