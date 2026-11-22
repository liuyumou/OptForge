"""Final settled checkpoint; preserves every failed receipt and original allocation."""
import re
from lp_billion_common import BASE,ROOT,load,put,ref,resolve,require,CPU_CAPS,GPU_CAPS
from lp_billion_budget import accounting

def main():
    reservations=list((BASE/'resources').glob('*.reservation.json'))
    require(all(p.with_name(p.name.replace('.reservation.','.settlement.')).exists() for p in reservations),'all reservations settled')
    gate=BASE/'resources/gpu-control-verification-v2.settlement.json';s=load(gate)
    require(s['status']=='passed' and s['cleanup_empty'] and not s['overrun'],'complete final verification')
    proof_path=BASE/'gpu-control-verification-v2/result.json';proof=load(proof_path);require(proof['status']=='passed','final proof')
    cpu,gpu=accounting();require(all(cpu[k]<=v*1e9 for k,v in CPU_CAPS.items()) and all(gpu[k]<=v*1e9 for k,v in GPU_CAPS.items()),'all phase caps')
    failed=[]
    for p in sorted((BASE/'resources').glob('*.settlement.json')):
        d=load(p)
        if d['status']!='passed':failed.append(dict(settlement=ref(p),**d))
    docs=next(c for c in proof['commands'] if c['name']=='documentation');pages=int(re.search(r'documentation built: (\d+) pages',resolve(docs['stdout']).read_text()).group(1))
    harness=next(c for c in proof['commands'] if c['name']=='harness');tests=int(re.search(r'Ran (\d+) tests',resolve(harness['stderr']).read_text()).group(1))
    summary=(f"Open settled allocation: {sum(cpu.values())/1e9:.9f} CPU / {sum(gpu.values())/1e9:.9f} GPU seconds within 370000 / 44000. "
             f"No reservation is active. {tests} harness tests and {pages} documentation pages/local links pass. "
             f"{len(proof['current_numerical_bindings'])} current numerical bindings verify; {len(proof['unchanged_numerical_bindings'])} prior bindings remain exact, with seven scoped integration changes and their original source copies retained. "
             f"{len(failed)} failed reservations retain {sum(x['cpu_ns'] for x in failed)/1e9:.9f} CPU / {sum(x['gpu_ns'] for x in failed)/1e9:.9f} GPU seconds. "
             "Evidence: `gpu-control-settled-checkpoint-v1.json`; compact checkpoint: `docs/benchmarks/lp-billion-gpu-control-checkpoint.json`.")
    for name in ['AGENTS.md','state/active-task.md','docs/benchmarks/lp-billion.md']:
        p=ROOT/name;text=p.read_text();require(text.count('GPU_CONTROL_SETTLEMENT_PENDING')==1,'one settlement placeholder '+name);p.write_text(text.replace('GPU_CONTROL_SETTLEMENT_PENDING',summary))
    previous=load(BASE/'gpu-pack-settled-checkpoint-v1.json')
    value=dict(status='open_settled',cpu_ns=sum(cpu.values()),gpu_ns=sum(gpu.values()),cpu_by_phase_ns=cpu,gpu_by_phase_ns=gpu,cpu_caps=CPU_CAPS,gpu_caps=GPU_CAPS,
        active_reservations=0,failed_reservations=len(failed),failures=failed,failed_cpu_ns=sum(x['cpu_ns'] for x in failed),failed_gpu_ns=sum(x['gpu_ns'] for x in failed),
        numerical_bindings=proof['current_numerical_bindings'],unchanged_prior_bindings=len(proof['unchanged_numerical_bindings']),scoped_changes=proof['changed_bindings'],
        documentation_pages=pages,harness_tests=tests,independent_checks=proof['independent_checks'],assessment_claims=proof['assessment_claims'],equal_update_comparisons=proof['equal_update_comparisons'],
        all_owned_identities_gone=proof['all_owned_identities_gone'],owned_process_identities_checked=proof['owned_process_identities_checked'],
        final_device_observation=proof['final_device_observation'],verification=ref(proof_path),verification_settlement=ref(gate),
        report=ref(ROOT/'docs/benchmarks/lp-billion.md'),results=proof['report'],phases=proof['phases'],previous_checkpoint=ref(BASE/'gpu-pack-settled-checkpoint-v1.json'),
        approval=ref(BASE/'approved-assessment-extension-v1.json'),storage_inventory_admission=proof['storage_inventory_admission'],
        data_retention=proof['data_retention'],historical_report_source=proof['historical_report_source'],general_allocation_unchanged=previous['general_allocation_unchanged'],fresh_full_portable_replay=False,public_adoption=False,confirmation=False,source=ref(__file__))
    target=BASE/'gpu-control-settled-checkpoint-v1.json';put(target,value);put(ROOT/'docs/benchmarks/lp-billion-gpu-control-checkpoint.json',dict(value,checkpoint=ref(target)))
    print(summary,flush=True)
if __name__=='__main__':main()
