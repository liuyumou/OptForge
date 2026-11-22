"""Retain the admitted CPU timing/COPT evidence without claiming billion results."""
from pathlib import Path
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require,CPU_CAPS,GPU_CAPS
from lp_billion_budget import accounting
from lp_confirmation2_supervisor import same_process


def numerical(name):
    return name.endswith(('.rs','.cu')) or Path(name).name.startswith('Cargo.')


def main():
    before=load(BASE/'image-v7/binding.json');after=load(BASE/'image-v8/binding.json')
    for key in ['cuda','preparation']:
        require(ref(resolve(before[key]))['sha256']==ref(resolve(after[key]))['sha256'],'unchanged CUDA '+key)
    allowed={'research/lp-billion-lowbit/'+p for p in ['src/billion.rs','src/bin/billion.rs','src/lib.rs']}
    old=[];exact=[];changed=[];guards=[]
    for item in load(resolve(before['source_manifest']))['sources']:
        name=item['original']['path']
        if numerical(name):
            resolve(item['retained']);old.append(name);current=ref(ROOT/name)
            if current==item['original']:exact.append(current)
            else:
                require(name in allowed,'unexpected numerical change '+name)
                changed.append(dict(before=item['retained'],after=current))
        if name in ['tools/lp_billion_budget.py','tools/lp_billion_common.py','tools/lp_billion_idle.py',
                    'tools/lp_confirmation2_supervisor.py','tools/lp_confirmation_supervisor.py','tools/lp_mixed2_reuse_place.py']:
            resolve(item['original']);guards.append(item['original'])
    current=[]
    for item in load(resolve(after['source_manifest']))['sources']:
        if numerical(item['original']['path']):
            resolve(item['original']);resolve(item['retained']);current.append(item['original'])
    added=[p for p in current if p['path'] not in old]
    require((len(old),len(exact),len(changed),len(current),len(added),len(guards))==(296,293,3,297,1,6),'complete timing source coverage')
    require(load(BASE/'build-timing-v3/result.json')['rust_tests']==57,'complete Rust quality')
    copt=load(BASE/'copt-native-cpu-v2/result.json')
    require(copt['status']=='passed' and len(copt['cases'])==12 and sum(c['certified'] for c in copt['cases'])==9,'complete COPT admission')
    from lp_billion_copt import installation
    require(copt['adapter']==ref(ROOT/'tools/lp_billion_copt.py') and copt['installation']==installation(),'COPT source/library exact')
    for c in copt['cases']:
        r=load(resolve(c['response']));resolve(c['model'])
        require(r['roundtrip_checked'] and sum(c['exclusive_ns'].values())==c['complete_ns'],'COPT roundtrip and cost accounting')
        if c['check']:require(load(resolve(c['check']))['accepted']==c['certified'],'strict COPT endpoint binding')
    for name in ['timing-quality-v3','timing-seal-v1','timing-copt-contracts-v3','copt-native-cpu-v2']:
        s=load(BASE/'resources'/(name+'.settlement.json'))
        require(s['status']=='passed' and s['cleanup_empty'] and not s['overrun'] and s['gpu_ns']==0,'supervised CPU gate '+name)
    for kind in ['gpu','memcheck','racecheck','initcheck','synccheck']:
        require(not (BASE/'resources'/('timing-'+kind+'-v1.reservation.json')).exists(),'timing GPU work remains unattempted')
    failures=[];new_cleanup=[]
    for p in sorted((BASE/'resources').glob('*.settlement.json')):
        s=load(p)
        if s['status']!='passed':failures.append(dict(settlement=ref(p),cpu_ns=s['cpu_ns'],gpu_ns=s['gpu_ns']))
        if p.name in [name+'.settlement.json' for name in ['timing-quality-v1','timing-quality-v2','timing-copt-contracts-v1','copt-native-cpu-v1']]:
            r=load(resolve(s['resource']))
            identities={(i['pid'],i['start_ticks']):i for i in r['guardian_cleanup']['killed']+r['result']['cleanup']['killed']}
            require(s['cleanup_empty'] and not any(same_process(i) for i in identities.values()),'failed attempt cleanup')
            new_cleanup.append(dict(settlement=ref(p),identities=list(identities.values()),all_absent=True))
    require(len(failures)==21 and sum(f['cpu_ns'] for f in failures)==39_060_000_000_000
            and sum(f['gpu_ns'] for f in failures)==1_800_000_000_000,'all retained failures and full charges')
    plan=load(BASE/'billion-comparison-plan-v1.json')
    require(len(plan['cells'])==30 and plan['billion_solves']==0 and plan['status']=='prospective_not_frozen','unfrozen complete roster')
    cpu,gpu=accounting()
    result=dict(status='CPU_timing_and_COPT_admitted_GPU_and_billion_comparison_pending',
        image=ref(BASE/'image-v8/binding.json'),rust_tests=57,python_contract_tests=35,
        copt_admission=ref(BASE/'copt-native-cpu-v2/result.json'),copt_cases=12,strict_accepted_endpoints=9,
        copt_cases_detail=copt['cases'],copt_installation=copt['installation'],
        source_bindings=current,unchanged_numerical_bindings=293,changed=changed,added=added,unchanged_guards=guards,
        gpu_validation_started=False,billion_solves=0,comparison=ref(BASE/'billion-comparison-plan-v1.json'),
        host_capacity=ref(BASE/'billion-host-availability-v5.json'),failures=failures,new_failed_cleanup=new_cleanup,
        cpu_caps=CPU_CAPS,gpu_caps=GPU_CAPS,cpu_ns_including_active_reservations=cpu,gpu_ns_including_active_reservations=gpu,
        allocation_open=True,prior_capacity_counts=dict(cells=38,responses=37,eligible_timings=35,missing=1),
        prior_CPU_packing_counts=dict(cells=18,responses=18,eligible_timings=12,excluded=6),
        portable_replay_claim=False,claim='CPU-only implementation/admission; no new GPU preparation or billion-scale performance comparison.')
    put(BASE/'timing-copt-delivery-v1.json',result)
    compact={k:v for k,v in result.items() if k not in ['source_bindings','copt_cases_detail','new_failed_cleanup']}
    compact['delivery']=ref(BASE/'timing-copt-delivery-v1.json')
    compact['copt_cases']=[dict(name=c['name'],status=c['status'],strict_certified=c['certified'],response=c['response'],check=c['check']) for c in copt['cases']]
    put(ROOT/'docs/benchmarks/lp-billion-timing-copt-results.json',compact)
    print(dict(status=result['status'],source_bindings=len(current),failed_reservations=len(failures)),flush=True)


if __name__=='__main__':main()
