"""Metadata-only pilot disposition, immutable-source audit and accounting."""
import hashlib
import json
from pathlib import Path
import statistics

from lp_fp4_gpu_common import BASE, ROOT, CPU_CAPS, GPU_CAPS, load, put, ref, checked, require
from lp_fp4_gpu_budget import accounting
from lp_fp4_gpu_study import MANIFEST, cells

DEST=ROOT/'docs/benchmarks/data'

def main():
    before=load(BASE/'prior-tracked.json')
    differences=[name for name,digest in before.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
    require(not differences,'historical source/evidence mutation: '+str(differences))
    m=load(MANIFEST) if MANIFEST.exists() else None
    if m:
        for item in m['sources']+[m['binary'],m['image'],m['build'],m['ptx'],m['sass'],m['inventory'],m['cpu_acceptance'],m['kernel_path_bridge']]:checked(item)
    rows=[];profile_receipts=[]
    for path in sorted(BASE.glob('profiles-*.json')):
        summary=load(path);require(summary['status']=='passed','profile status')
        rows.extend(summary['rows']);profile_receipts.append(ref(path))
    by_id={row['id']:row for row in rows};require(len(by_id)==len(rows),'duplicate profile identity')
    outcomes=[]
    for cell in cells():
        row=by_id.get(cell['id'])
        outcomes.append(dict(cell,disposition='completed' if row else 'unexecuted',result=row))
    gates={}
    for name in ('primitive','device','memcheck','racecheck','initcheck','synccheck'):
        p=BASE/(name+'.json');gates[name]=dict(status=load(p)['status'],receipt=ref(p)) if p.exists() else dict(status='unexecuted_or_refused')
    summaries=[]
    if len(rows)==216:
        for name in ('dense-32','irregular-29','dense-2048'):
            for variant in ('split','fused','persistent','roundtrip'):
                native=[r for r in rows if r['workload']==name and r['variant']==variant and r['format']==64]
                for f,k in [(64,1),(8,4),(16,2),(4,2),(4,4),(4,8)]:
                    selected=[r for r in rows if r['workload']==name and r['variant']==variant and r['format']==f and r['components']==k]
                    require(len(selected)==3,'repetition coverage')
                    cold=[r['cold_ns'] for r in selected];iteration=[r['phases_ns']['iteration'] for r in selected]
                    summaries.append(dict(workload=name,variant=variant,format=f,components=k,
                        cold_median_ns=statistics.median(cold),cold_range_ns=[min(cold),max(cold)],
                        iteration_median_ns=statistics.median(iteration),iteration_range_ns=[min(iteration),max(iteration)],
                        cold_speedup=statistics.median(r['cold_ns'] for r in native)/statistics.median(cold),
                        iteration_speedup=statistics.median(r['phases_ns']['iteration'] for r in native)/statistics.median(iteration),
                        max_observed_error=max(r['observation']['max_absolute'] for r in selected),
                        max_primal_residual=max(r['original_a_primal_residual'] for r in selected)))
    cpu,gpu=accounting();resources=[]
    for path in sorted((BASE/'resources').glob('*.reservation.json')):
        settlement=path.with_name(path.name.replace('.reservation.json','.settlement.json'))
        item=load(settlement) if settlement.exists() else load(path)
        report=path.with_name(path.name.replace('.reservation.json','.resource.json'))
        cleanup=None
        if report.exists():
            receipt=load(report);cleanup=receipt.get('guardian_cleanup',{}).get('empty') and receipt.get('result',{}).get('cleanup',{}).get('empty')
            require(cleanup,'nonempty cleanup receipt')
        resources.append(dict(reservation=ref(path),settlement=ref(settlement) if settlement.exists() else None,cleanup_empty=cleanup,status=item.get('status','unsettled')))
    require(all(cpu[p]<=cap*10**9 for p,cap in CPU_CAPS.items()),'CPU cap exceeded')
    require(all(gpu[p]<=cap*10**9 for p,cap in GPU_CAPS.items()),'GPU cap exceeded')
    # The supervised delivery reservation is deliberately included in full while active.
    result=dict(kind='fp4-gpu-pilot-result-v1',completed=len(rows),planned=216,certified=0,
        status='complete_empirical_pilot' if len(rows)==216 and all(g['status']=='passed' for g in gates.values()) else 'blocked',
        cells=outcomes,summaries=summaries,gates=gates,profile_receipts=profile_receipts,
        manifest=ref(MANIFEST) if m else None,historical_files_preserved=len(before),historical_hashes=ref(BASE/'prior-tracked.json'),
        limitations=['Block-diagonal 32-variable independent blocks only; no coupled sparse LP integration.',
                     'Empirical differences/residuals are not certified bounds or solver convergence.',
                     'CUDA stream span includes host submission gaps; it is not isolated kernel busy time.',
                     'Cold cost includes CPU preparation and process execution; no certified endpoint/checker cost exists.',
                     'Three repetitions report ranges, not statistically established acceleration.'])
    put(DEST/'fp4-gpu-pilot-result-v1.json',result)
    put(DEST/'fp4-gpu-pilot-accounting-v1.json',dict(cpu_ns=cpu,gpu_ns=gpu,cpu_cap_seconds=CPU_CAPS,gpu_cap_seconds=GPU_CAPS,
        total_cpu_ns=sum(cpu.values()),total_gpu_ns=sum(gpu.values()),resources=resources,
        note='Active delivery reservation charged fully; final settled receipt is additive. Closed historical budgets unchanged.'))
    print(json.dumps(dict(status=result['status'],completed=len(rows),cpu_seconds=sum(cpu.values())/1e9,gpu_seconds=sum(gpu.values())/1e9)))

if __name__=='__main__':main()
