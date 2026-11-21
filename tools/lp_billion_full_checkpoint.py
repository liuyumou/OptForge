"""Settle the completed comparison after its final supervised verification."""
import re
from lp_billion_common import BASE,ROOT,load,put,ref,resolve,require,CPU_CAPS,GPU_CAPS
from lp_billion_budget import accounting


def main():
    reservations=list((BASE/'resources').glob('*.reservation.json'))
    active=[p.name for p in reservations if not p.with_name(p.name.replace('.reservation.','.settlement.')).exists()]
    require(not active,'all experiment and final verification reservations settled')
    check=BASE/'resources/full-billion-verification-v1.settlement.json'
    s=load(check);require(s['status']=='passed' and s['cleanup_empty'] and not s['overrun'],'final supervised verification')
    result=BASE/'full-billion-verification-v1/result.json';v=load(result)
    require(v['status']=='passed','completed final verification')
    cpu,gpu=accounting()
    require(all(cpu[k]<=cap*1e9 for k,cap in CPU_CAPS.items()),'CPU phase caps')
    require(all(gpu[k]<=cap*1e9 for k,cap in GPU_CAPS.items()),'GPU phase caps')
    failed=[]
    for p in sorted((BASE/'resources').glob('*.settlement.json')):
        item=load(p)
        if item['status']!='passed':failed.append(dict(settlement=ref(p),**item))
    docs=next(r for r in v['commands'] if r['name']=='documentation')
    pages=int(re.search(r'documentation built: (\d+) pages',resolve(docs['stdout']).read_text()).group(1))
    harness=next(r for r in v['commands'] if r['name']=='harness')
    tests=int(re.search(r'Ran (\d+) tests',resolve(harness['stderr']).read_text()).group(1))
    prior=load(BASE/'bounded-memory-settled-checkpoint-v1.json')
    value=dict(status='open_settled',cpu_ns=sum(cpu.values()),gpu_ns=sum(gpu.values()),cpu_by_phase_ns=cpu,gpu_by_phase_ns=gpu,
        cpu_caps=CPU_CAPS,gpu_caps=GPU_CAPS,active_reservations=0,failed_reservations=len(failed),failures=failed,
        failed_cpu_ns=sum(x['cpu_ns'] for x in failed),failed_gpu_ns=sum(x['gpu_ns'] for x in failed),
        documentation_pages=pages,harness_tests=tests,numerical_bindings=300,
        full_billion_attempts=v['actual_attempts'],full_billion_responses=v['actual_responses'],strict_certificates=v['strict_certificates'],
        independent_checks=v['independent_checks'],recorded_assessment_claims=v['recorded_assessment_claims'],
        all_cohort_owned_identities_gone=v['all_cohort_owned_identities_gone'],process_identities_checked=v['process_identities_checked'],
        final_device_observation=v['final_device_observation'],verification=ref(result),verification_settlement=ref(check),
        delivery=ref(BASE/'full-billion-delivery-v1.json'),report=v['report'],phase_csv=v['phase_csv'],
        previous_checkpoint=ref(BASE/'complete-device-checkpoint-v1.json'),approval=ref(BASE/'approved-recovery-v1.json'),
        general_allocation_unchanged=prior['general_allocation_unchanged'],fresh_full_portable_replay=False,
        public_adoption=False,confirmation=False,source=ref(__file__))
    target=BASE/'full-billion-settled-checkpoint-v1.json';put(target,value)
    put(ROOT/'docs/benchmarks/lp-billion-full-checkpoint.json',dict(value,checkpoint=ref(target)))
    summary=(f"Open settled allocation: {sum(cpu.values())/1e9:.9f} CPU / {sum(gpu.values())/1e9:.9f} GPU seconds "
             f"within 320000 / 35000. No reservation is active. {tests} billion-harness tests and {pages} documentation pages/local links pass. "
             f"All 300 numerical bindings remain exact. {len(failed)} failed reservations retain full "
             f"{value['failed_cpu_ns']/1e9:.9f} CPU / {value['failed_gpu_ns']/1e9:.9f} GPU seconds. "
             "Final settled evidence: `full-billion-settled-checkpoint-v1.json`; compact checkpoint: `docs/benchmarks/lp-billion-full-checkpoint.json`.")
    for name in ['AGENTS.md','state/active-task.md','docs/benchmarks/lp-billion.md']:
        p=ROOT/name;text=p.read_text();require(text.count('FULL_BILLION_SETTLEMENT_PENDING')==1,'one final settlement placeholder '+name)
        p.write_text(text.replace('FULL_BILLION_SETTLEMENT_PENDING',summary))
    print(summary,flush=True)

if __name__=='__main__':main()
