"""Separate Presolve=0 COPT GPU study; never changes or retries the baseline."""
import argparse,math,resource,subprocess,time
from pathlib import Path
from lp_billion_common import BASE,ROOT,NS,CPU_CAPS,GPU_CAPS,DISK_LIMIT,put,load,ref,resolve,require,disk_bytes
from lp_billion_budget import accounting,run
from lp_billion_prepare_continue import completed
from lp_billion_owned_process import execute as child
from lp_billion_full_plan import FAMILIES,FINAL
from lp_billion_copt_readiness import gpu_peak,workspace_observed
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'
ADAPTER=ROOT/'tools/lp_billion_copt_nopresolve.py'
AUDIT=ROOT/'tools/lp_billion_full_audit_v2.py'
PROTOCOL=ROOT/'docs/specifications/SPEC-0046-amendment-49.md'
PREFIX='copt-nopresolve'
GIB=1<<30

def bounded_group(rows,model):
    valid=bool(rows) and all(r['capacity_observed'] for r in rows)
    host=math.ceil(max((r['host_peak_bytes']*1e9/r['nonzeros'] for r in rows),default=0)*1.15)+8*GIB
    device=math.ceil(max((r['owned_device_peak_bytes']*1e9/r['nonzeros'] for r in rows),default=0)*1.15)+4*GIB
    vendor=max((r['vendor_mem_peak_mb']*1e9/r['nonzeros'] for r in rows),default=0)
    imports=24*model['nonzeros']+44*model['columns']+24*model['rows']
    reasons=[]
    if not valid:reasons.append('missing/interrupted/unconfirmed optimization workspace')
    if host>128*GIB:reasons.append('host forecast exceeds 128 GiB')
    if device>80*GIB:reasons.append('device forecast exceeds 80 GiB')
    if vendor>48000:reasons.append('vendor peak forecast exceeds unchanged 48000 MB soft setting')
    if imports+8*GIB>128*GIB:reasons.append('adapter import arrays exceed host allowance')
    return dict(admitted=not reasons,reasons=reasons,host_gib=128,device_gib=80,host_bytes=128*GIB,device_bytes=80*GIB,
        empirical_host_peak_with_allowance=host,empirical_device_peak_with_allowance=device,forecast_vendor_mem_peak_mb=vendor,
        adapter_import_arrays_bytes=imports,forecast_is_hard_enclosure=False,vendor_memory_limit_is_soft=True,
        source_cells=[r['id'] for r in rows])

def capacity():
    rows=[];evidence=[]
    for tag in ['64m','256m','512m']:
        path=BASE/f'{PREFIX}-{tag}-v1/freeze.json';f=load(path)
        require((path.parent/'completed.json').exists(),'complete separate capacity stage');evidence.append(ref(path))
        for c in f['cells']:
            sp=BASE/'resources'/(c['id']+'.settlement.json');s=load(sp);evidence.append(ref(sp))
            rp=BASE/c['id']/'response.json';r=load(rp) if rp.exists() else None
            telemetry=BASE/'resources'/(c['id']+'.resource.json.capacity.jsonl');peak=gpu_peak(telemetry) if telemetry.exists() else 0
            if telemetry.exists():evidence.append(ref(telemetry))
            check=load(BASE/(c['id']+'-full-audit/result.json'));evidence.append(ref(BASE/(c['id']+'-full-audit/result.json')))
            valid=s['status']=='passed' and s['cleanup_empty'] and not s['overrun'] and r is not None and r['gpu_confirmed'] and peak>0 and workspace_observed(r,check.get('certified',False))
            if r is not None:
                evidence.append(ref(rp));require(r['parameters']['Presolve']==0,'separate configuration identity')
            host=r['host_memory']['VmHWM'] if r else 0
            aggregate=load(resolve(s['resource']))['result'].get('peak_rss_bytes',0)
            if valid:require(aggregate-host<=8*GIB,'bounded constant coordinator allowance')
            rows.append(dict(id=c['id'],family=c['family'],nonzeros=load(resolve(c['model_result']))['nonzeros'],capacity_observed=bool(valid),
                host_peak_bytes=host,owned_device_peak_bytes=peak,vendor_mem_peak_mb=r['native']['MemPeak'] if r else 0.,
                native=r['native'] if r else None,status=r['status'] if r else 'missing_response',strict_certified=check.get('certified',False)))
    capacities={f:bounded_group([r for r in rows if r['family']==f],load(BASE/f'models-1b-{f}-v1/result.json')) for f in FAMILIES}
    put(BASE/f'{PREFIX}-capacity-v1.json',dict(status='complete_capacity_dispositions',cells=rows,capacity=capacities,evidence=evidence,source=ref(__file__),adapter=ref(ADAPTER),protocol=ref(PROTOCOL)))

def freeze(tag):
    require(completed('copt-nopresolve-contracts-v1') and completed('copt-nopresolve-admission-v1'),'source-specific variant admission')
    gate=load(BASE/'copt-nopresolve-admission-v1/result.json');require(gate['adapter']==ref(ADAPTER),'admitted variant source')
    paths=[BASE/f'models-1b-{f}-v1/result.json' for f in FAMILIES] if tag=='1b' else sorted(BASE.glob(f'models-{tag}-*-v1/result.json'))
    require(len(paths)==(6 if tag in ['64m','1b'] else 2),'complete original family roster')
    cells=[]
    caps=load(BASE/f'{PREFIX}-capacity-v1.json')['capacity'] if tag=='1b' else None
    for i,path in enumerate(paths):
        m=load(path);family=m['family'];sec={'64m':240,'256m':360,'512m':600,'1b':1100 if family=='wide' else 900}[tag]
        mem=caps[family] if caps else dict(admitted=True,host_gib=128,device_gib=80)
        cells.append(dict(id=f'{PREFIX}-{tag}-v1-{i}',family=family,lane='copt-gpu-pdlp-presolve0',model=m['model'],model_result=ref(path),
            status='pending' if mem['admitted'] else 'unsupported_capacity',memory=mem,seconds=sec,
            audit_seconds=FINAL[family] if tag=='1b' else {'64m':90,'256m':180,'512m':300}[tag],
            wall_seconds={'64m':90,'256m':180,'512m':300,'1b':600}[tag],memory_mb=48000.,disk_gib=math.ceil(8*(m['columns']+2*m['rows'])/GIB)+1))
    live=[c for c in cells if c['status']=='pending'];cpu,gpu=accounting()
    require(cpu['development']+4*sum(c['seconds'] for c in live)*NS<=CPU_CAPS['development']*NS,'whole separate stage solve CPU')
    require(gpu['development']+sum(c['seconds'] for c in live)*NS<=GPU_CAPS['development']*NS,'whole separate stage GPU')
    require(cpu['reporting']+(4*sum(c['audit_seconds'] for c in live)+1200)*NS<=CPU_CAPS['reporting']*NS,'whole separate stage audits and final reporting')
    require(disk_bytes()+(sum(c['disk_gib'] for c in live)+8)*GIB<=DISK_LIMIT,'whole separate stage endpoints and repaired witnesses')
    from lp_billion_copt_nopresolve import installation
    put(BASE/f'{PREFIX}-{tag}-v1/freeze.json',dict(status='frozen_separate_development',cells=cells,source=ref(__file__),adapter=ref(ADAPTER),
        installation=installation(),checker=ref(BASE/'image-v1/executor'),audit=ref(AUDIT),child=ref(ROOT/'tools/lp_billion_owned_process.py'),protocol=ref(PROTOCOL),
        admission=ref(BASE/'copt-nopresolve-admission-v1/result.json'),capacity=ref(BASE/f'{PREFIX}-capacity-v1.json') if caps else None,
        claim='Separate Presolve=0 GPU configuration. Every baseline outcome remains unchanged; no scientific cell retries.'))

def worker(manifest,index):
    f=load(manifest);c=f['cells'][index]
    for key in ['source','adapter','audit','child']:resolve(f[key])
    from lp_billion_copt_nopresolve import installation
    require(f['installation']==installation(),'installed library identity');require(c['status']=='pending','supported cell only')
    out=BASE/c['id'];out.mkdir(exist_ok=False);response=out/'response.json'
    prior=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    p=child([str(PYTHON),'-B',str(ADAPTER),str(resolve(c['model'])),str(response),'--gpu','--wall-seconds',str(c['wall_seconds']),
        '--memory-mb',str(c['memory_mb'])],out/'stdout',out/'stderr',c['seconds']-30)
    p.update(child_rusage_hwm_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss*1024,child_rusage_scope_is_single_solver=prior==0)
    put(out/'process.json',p);require(not p['timed_out'] and p['returncode']==0,'retained owned child interruption; never retry')
    start=time.monotonic_ns();r=load(response)
    require(r['model_sha256']==c['model']['sha256'] and r['parameters']['Presolve']==0,'original model and variant binding')
    require(r['nonzeros']==load(resolve(c['model_result']))['nonzeros'],'original nonzero count')
    require(sum(r['profile']['exclusive_ns'].values())==r['profile']['total_ns']<=p['elapsed_ns'],'exact outer timing coverage')
    transport=time.monotonic_ns()-start
    put(out/'result.json',dict(response=ref(response),freeze=ref(manifest),process_ns=p['elapsed_ns'],response_transport_ns=transport,fresh_process_ns=p['elapsed_ns']+transport,
        solver_child_hwm_bytes=p['child_rusage_hwm_bytes'] if prior==0 else None))

def execute(tag):
    manifest=BASE/f'{PREFIX}-{tag}-v1/freeze.json';f=load(manifest)
    for i,c in enumerate(f['cells']):
        if c['status']!='pending':continue
        rp=BASE/'resources'/(c['id']+'.reservation.json')
        if not rp.exists():s=run(c['id'],'development',c['seconds'],True,[str(PYTHON),'-B',__file__,'worker','--manifest',str(manifest),'--index',str(i)],128,80,c['disk_gib'])
        else:s=load(rp.with_name(c['id']+'.settlement.json'))
        print(dict(cell=c['id'],settlement=s),flush=True);require(s['cleanup_empty'] and not s['overrun'],'cleanup/overrun stops continuation')
        name=c['id']+'-full-audit'
        if not (BASE/'resources'/(name+'.reservation.json')).exists():
            s=run(name,'reporting',c['audit_seconds'],False,[str(PYTHON),'-B',str(AUDIT),str(manifest),str(i)],64,0,c['disk_gib'])
            print(dict(audit=name,settlement=s),flush=True);require(s['status']=='passed','strict independent audit stops continuation')
        else:require(completed(name),'retain failed audit')
    put(manifest.parent/'completed.json',dict(status='all_supported_cells_attempted_and_available_endpoints_audited',freeze=ref(manifest)))

def admission_worker():
    out=BASE/'copt-nopresolve-admission-driver-v1';out.mkdir(exist_ok=False)
    p=child([str(PYTHON),'-B',str(ROOT/'tools/lp_billion_copt_nopresolve_admit.py'),'--id','copt-nopresolve-admission-v1'],out/'stdout',out/'stderr',420)
    put(out/'process.json',p);require(not p['timed_out'] and p['returncode']==0,'variant admission stopped with retained evidence')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','execute','worker','capacity','admission_worker']);p.add_argument('--tag',choices=['64m','256m','512m','1b']);p.add_argument('--manifest',type=Path);p.add_argument('--index',type=int);a=p.parse_args()
    if a.action=='worker':worker(a.manifest,a.index)
    elif a.action in ['freeze','execute']:globals()[a.action](a.tag)
    else:globals()[a.action]()
