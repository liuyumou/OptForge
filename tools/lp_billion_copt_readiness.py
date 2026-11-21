"""Source-bound capacity dispositions; opaque vendor peaks remain empirical."""
import math
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require
from lp_billion_full_plan import FAMILIES,LANES
GIB=1<<30

def gpu_peak(path):
    peak=0
    for line in path.read_text().splitlines():
        s=__import__('json').loads(line);owned={str(p) for p in s['owned_physical_pids']}
        peak=max(peak,sum(v for p,v in s['gpu']['processes'].items() if p in owned))
    return peak

def workspace_observed(response,strict_accepted=False):
    if response is None or not response['solve_called'] or response['solve_returncode']!=0:return False
    native=response['native']
    iterations=sum(native[k] for k in ['SimplexIter','BarrierIter','PDLPIter'])
    return iterations>0 or (response['optimal'] and response['has_solution'] and strict_accepted)

def main():
    manifests=[BASE/'copt-capacity-64m-v1/freeze.json',*[BASE/f'copt-capacity-{t}-tail-v1/freeze.json' for t in ['64m','256m','512m']]]
    for t in ['64m','256m','512m']:require((BASE/f'copt-capacity-{t}-tail-v1/completed.json').exists(),'complete prospective capacity stage')
    cells={};evidence=[]
    for p in manifests:
        f=load(p);evidence.append(ref(p))
        for c in f['cells']:cells[c['id']]=c
    rows=[]
    for identity,c in cells.items():
        path=BASE/'resources'/(identity+'.settlement.json');s=load(path);evidence.append(ref(path))
        rpath=BASE/identity/'response.json';r=load(rpath) if rpath.exists() else None
        resource=load(resolve(s['resource']));m=load(resolve(c['model_result']))
        if r is not None:evidence.append(ref(rpath))
        telemetry=BASE/'resources'/(identity+'.resource.json.capacity.jsonl')
        peak=gpu_peak(telemetry) if c['lane']=='copt-gpu-pdlp' and telemetry.exists() else 0
        if telemetry.exists():evidence.append(ref(telemetry))
        valid=s['status']=='passed' and s['cleanup_empty'] and not s['overrun'] and r is not None and r['solve_called'] and r['solve_returncode']==0
        if c['lane']=='copt-gpu-pdlp':valid=valid and r is not None and r['gpu_confirmed'] and peak>0
        check=None
        if r is not None and r['has_solution']:
            check=BASE/(identity+'-full-audit/result.json')
            require(check.exists() and load(check)['status']=='passed','every available capacity endpoint independently checked')
            evidence.append(ref(check))
        work_observed=workspace_observed(r,bool(check and load(check)['certified']))
        valid=valid and work_observed
        host=r['host_memory']['VmHWM'] if r else 0
        aggregate=resource['result'].get('peak_rss_bytes',0)
        if valid:require(aggregate-host<=8*GIB,'observed coordinator allowance exceeds full host reserve')
        rows.append(dict(id=identity,family=c['family'],lane=c['lane'],nonzeros=m['nonzeros'],capacity_observed=bool(valid),
            host_peak_bytes=host,sampled_aggregate_peak_rss_bytes=aggregate,owned_device_peak_bytes=peak,settlement=ref(path),response=ref(rpath) if r else None,
            strict_certified=bool(check and load(check)['certified']),solver_status=r['status'] if r else None,optimization_workspace_observed=work_observed,
            optimization_iterations=sum(r['native'][k] for k in ['SimplexIter','BarrierIter','PDLPIter']) if r else None,
            vendor_mem_peak_mb=r['native']['MemPeak'] if r else None,
            full_charge_retained=s['status']!='passed',timing_eligible=s['status']=='passed'))
    capacity={}
    for family in FAMILIES:
        capacity[family]={}
        for lane in LANES[3:]:
            group=[r for r in rows if r['family']==family and r['lane']==lane]
            failed=[r for r in group if not r['capacity_observed']]
            valid=[r for r in group if r['capacity_observed']]
            observed=[r for r in group if r['response'] is not None]
            reason=None
            if not valid or failed:reason='retained missing/interrupted/unconfirmed capacity path or optimization workspace unvalidated'
            # Use the child process HWM (vendor plus adapter). The separate 8 GiB
            # allowance covers the bounded coordinator, allocator and growth; do
            # not multiply constant supervisor RSS by the nonzero scale.
            # Include all observed scales rather than cherry-picking the lowest
            # per-nonzero peak. Reserve growth slack and fixed allocator/context
            # allowance; this is empirical admission, never a hard vendor bound.
            host=math.ceil(max((r['host_peak_bytes']*1_000_000_000/r['nonzeros'] for r in observed),default=0)*1.15)+(8*GIB)
            device=math.ceil(max((r['owned_device_peak_bytes']*1_000_000_000/r['nonzeros'] for r in observed),default=0)*1.15)+(4*GIB) if lane=='copt-gpu-pdlp' else 0
            vendor_mb=max((r['vendor_mem_peak_mb']*1_000_000_000/r['nonzeros'] for r in observed),default=0)
            if vendor_mb>48000:reason='reported vendor peak forecast exceeds the admitted 48000 MB soft setting; full workspace not admitted'
            model=load(BASE/f'models-1b-{family}-v1/result.json');import_arrays=24*model['nonzeros']+44*model['columns']+24*model['rows']
            if host>128*GIB or device>80*GIB:reason='empirical complete peak forecast plus growth allowance exceeds approved capacity'
            if import_arrays+8*GIB>128*GIB:reason='adapter import arrays plus allowance exceed host capacity'
            capacity[family][lane]=dict(admitted=reason is None,reason=reason,host_gib=128,device_gib=80 if lane=='copt-gpu-pdlp' else 0,
                host_bytes=128*GIB,device_bytes=80*GIB if lane=='copt-gpu-pdlp' else 0,
                empirical_host_peak_with_allowance=host,empirical_device_peak_with_allowance=device,adapter_import_arrays_bytes=import_arrays,
                forecast_is_hard_enclosure=False,vendor_memory_limit_is_soft=True,forecast_vendor_mem_peak_mb=vendor_mb,
                optimization_workspace_observed=bool(valid) and not failed,source_cells=[r['id'] for r in group])
    put(BASE/'copt-capacity-readiness-v1.json',dict(status='complete_capacity_dispositions',capacity=capacity,cells=rows,evidence=evidence,
        adapter=ref(ROOT/'tools/lp_billion_copt_run.py'),source=ref(__file__),protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-48.md'),
        claim='Empirical prospective capacity admission with unchanged sampled physical guards; no vendor hard memory enclosure.'))
    print({f:{l:c['admitted'] for l,c in lanes.items()} for f,lanes in capacity.items()},flush=True)
if __name__=='__main__':main()
