"""Audit current CPU packing evidence without claiming GPU or full-solve admission."""
from pathlib import Path
from lp_billion_common import BASE,ROOT,load,put,ref,resolve,require,CPU_CAPS,GPU_CAPS
from lp_billion_budget import accounting
from lp_billion_admit import gate_identity
from lp_confirmation2_supervisor import same_process


def numerical(name):
    return name.endswith(('.rs','.cu')) or Path(name).name.startswith('Cargo.')


def main():
    before=load(BASE/'image-v4/binding.json');after=load(BASE/'image-v7/binding.json')
    for key in ['cuda','preparation']:
        resolve(before[key]);resolve(after[key])
        require(before[key]['sha256']==after[key]['sha256'],'unchanged CUDA '+key)
    allowed={'research/lp-billion-lowbit/'+p for p in ['src/billion.rs','src/lib.rs','src/tensor.rs','tests/contracts.rs']}
    original=[];exact=[];changed=[];guards=[]
    for item in load(resolve(before['source_manifest']))['sources']:
        name=item['original']['path']
        if numerical(name):
            resolve(item['retained']);original.append(name);current=ref(ROOT/name)
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
    added=[p for p in current if p['path'] not in original]
    require((len(original),len(exact),len(changed),len(current),len(added),len(guards))==(293,289,4,296,3,6),'complete source coverage')
    require(load(BASE/'build-packing-v5/result.json')['rust_tests']==54,'complete final CPU acceptance')
    cohorts=[]
    for version in [1,2,3]:
        path=BASE/('packing-progress-v'+str(version)+'.json');result=load(path)
        require(len(result['cells'])==6,'full CPU roster')
        for row in result['cells']:
            measured=load(resolve(row['result']));raw=load(resolve(measured['raw']));settlement=load(resolve(row['settlement']))
            require(raw['exact'] and not raw['cuda_context_created'] and not raw['lp_solve_executed'],'CPU stage scope')
            require(settlement['status']=='passed' and settlement['cleanup_empty'] and not settlement['overrun'] and settlement['gpu_ns']==0,'complete CPU measurement supervision')
        built=load(resolve(result['diagnostic_build']))
        resolve(built['executable']);resolve(built['source'])
        if version>=2:
            resolve(built['library']);resolve(built['serde'])
        cohorts.append(dict(version=version,result=ref(path),timing_eligible=version>=2))
    disposition=load(BASE/'packing-cpu-build-v1/library-disposition.json')
    require(disposition['status']=='missing_intermediate_library' and disposition['timing_eligible'] is False,'retained first-cohort exclusion')
    cleanup_path=BASE/'resources/packing-quality-v3.cleanup-disposition.json';cleanup=load(cleanup_path)
    require(cleanup['status']=='cleanup_verified' and not any(same_process(p) for p in cleanup['identities']),'independent failed-quality cleanup')
    for version in [5,6,7]:
        for kind in ['gpu','memcheck','racecheck','initcheck','synccheck']:
            require(not (BASE/'resources'/(gate_identity(kind,version)+'.reservation.json')).exists(),'candidate GPU work unexpectedly attempted')
        for scale in ['64m','256m','512m']:
            require(not (BASE/f'ladder-{scale}-v{version}/freeze.json').exists(),'candidate full-solve cohort unexpectedly frozen')
    failures=[]
    for path in sorted((BASE/'resources').glob('*.settlement.json')):
        s=load(path)
        if s['status']!='passed':failures.append(dict(settlement=ref(path),cpu_ns=s['cpu_ns'],gpu_ns=s['gpu_ns']))
    require(len(failures)==17 and sum(p['cpu_ns'] for p in failures)==36_000_000_000_000 and
            sum(p['gpu_ns'] for p in failures)==1_800_000_000_000,'all historical failed charges')
    cpu,gpu=accounting()
    put(BASE/'packing-delivery-v1.json',dict(status='cpu_stage_validated_full_solve_unmeasured',
        final=ref(BASE/'packing-progress-v3.json'),cohorts=cohorts,
        missing_library_disposition=ref(BASE/'packing-cpu-build-v1/library-disposition.json'),
        quality_cleanup=ref(cleanup_path),image=ref(BASE/'image-v7/binding.json'),
        original_numerical_bindings=len(original),unchanged_numerical_bindings=len(exact),changed=changed,added=added,
        current_numerical_bindings=len(current),current_numerical_sources=current,unchanged_guards=guards,
        failed_reservations=failures,prior_full_solve_capacity_counts=dict(cells=38,responses=37,eligible_timings=35,missing=1),
        cpu_stage_counts=dict(cells=18,responses=18,eligible_timings=12,excluded=6),
        billion_host_gate=ref(BASE/'billion-host-availability-v3.json'),billion_solves=0,
        cpu_ns_including_active=sum(cpu.values()),gpu_ns_including_active=sum(gpu.values()),cpu_caps=CPU_CAPS,gpu_caps=GPU_CAPS,
        public_defaults_unchanged=True,strict_certificates_unchanged=True,source=ref(__file__),
        limitation='Paired CPU packing-stage diagnostics only; no new GPU admission, full-preparation or total-solve result. First cohort timings explicitly excluded; all regressions and failures retained.'))
    print(dict(status='passed',current_numerical_bindings=len(current),cpu_stage_cells=18,eligible_stage_cells=12,failed_reservations=len(failures)),flush=True)


if __name__=='__main__':main()
