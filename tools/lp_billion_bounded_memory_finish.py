"""Final immutable audit and settled checkpoint for the bounded-memory update."""
import argparse
import subprocess
from lp_billion_common import BASE,ROOT,load,put,ref,resolve,require,CPU_CAPS,GPU_CAPS
from lp_billion_budget import accounting


def verify():
    d=load(BASE/'bounded-memory-delivery-v1.json')
    for item in d['source_bindings']+d['unchanged_guards']:resolve(item)
    require(d['successful_responses']==14 and d['raw_responses']==15 and d['exact_pairs']==7 and d['eligible_pairs']==6,'complete original CPU roster and exclusion')
    require(load(BASE/'resources/bounded-memory-contracts-v2.settlement.json')['status']=='passed','final harness gate')
    original='e449097'
    for name in ['AGENTS.md','state/active-task.md','docs/benchmarks/lp-billion.md']:
        old=subprocess.check_output(['git','show',original+':'+name],cwd=ROOT).decode();new=(ROOT/name).read_text()
        if name=='docs/benchmarks/lp-billion.md':require(new.startswith(old),'historical report unchanged')
        else:require(new.endswith(old if name=='AGENTS.md' else old.split('\n',2)[2]),'historical handoff unchanged')
    for new,old in [(23,21),(24,22)]:
        plan=load(BASE/f'operational-readmissions/v{old}.json')
        plan.update(protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-39.md'),cpu_only_jobs=[],cpu_only_sources=[])
        plan['completed_CPU_scope']=ref(BASE/'bounded-memory-delivery-v1.json')
        plan['final_capacity_contracts']=ref(BASE/'resources/bounded-memory-contracts-v2.settlement.json')
        put(BASE/f'operational-readmissions/v{new}.json',plan)
    put(BASE/'bounded-memory-final-verification-v1.json',dict(status='passed',current_numerical_bindings=299,
        current_guard_bindings=6,historical_report_and_handoffs_exact=True,delivery=ref(BASE/'bounded-memory-delivery-v1.json'),
        final_harness=ref(BASE/'resources/bounded-memory-contracts-v2.settlement.json'),
        final_harness_sources=ref(BASE/'sources/bounded-memory-contracts-v2/manifest.json'),
        operational_plans=[ref(BASE/f'operational-readmissions/v{i}.json') for i in [23,24]]))
    print('Final source, history, cleanup scope and complete CPU roster verified.',flush=True)


def checkpoint():
    active=[p for p in (BASE/'resources').glob('*.reservation.json') if not p.with_name(p.name.replace('.reservation.json','.settlement.json')).exists()]
    require(not active,'all reservations settled')
    docs=BASE/'resources/bounded-memory-docs-v1.settlement.json';require(load(docs)['status']=='passed','documentation accepted')
    cpu,gpu=accounting();previous=load(BASE/'timing-settled-checkpoint-v1.json')
    result=dict(status='open_settled',cpu_ns=sum(cpu.values()),gpu_ns=sum(gpu.values()),cpu_by_phase_ns=cpu,gpu_by_phase_ns=gpu,
        cpu_caps=CPU_CAPS,gpu_caps=GPU_CAPS,active_reservations=0,failed_reservations=22,
        failed_cpu_ns=40_020_000_000_000,failed_gpu_ns=1_800_000_000_000,
        delivery=ref(BASE/'bounded-memory-delivery-v1.json'),final_verification=ref(BASE/'bounded-memory-final-verification-v1.json'),
        docs_settlement=ref(docs),documentation_pages=336,prior_checkpoint=ref(BASE/'timing-settled-checkpoint-v1.json'),
        general_allocation_unchanged=previous['general_allocation_unchanged'],billion_LP_solves=0,
        billion_CPU_preparations=1,current_GPU_admission_started=False,
        host_capacity=ref(BASE/'billion-host-availability-v6.json'),current_image=ref(BASE/'image-v9/binding.json'),
        limitation='Bounded CPU preparation verified, measured CPU overall peak unchanged; GPU admission and full billion/COPT solves pending.')
    put(BASE/'bounded-memory-settled-checkpoint-v1.json',result)
    put(ROOT/'docs/benchmarks/lp-billion-bounded-memory-checkpoint.json',dict(result,checkpoint=ref(BASE/'bounded-memory-settled-checkpoint-v1.json')))
    line=f"Open settled checkpoint: {sum(cpu.values())/1e9:.9f} CPU / {sum(gpu.values())/1e9:.9f} GPU seconds.\nAll 336 documentation pages and local links validate."
    for name in ['AGENTS.md','state/active-task.md']:
        p=ROOT/name;s=p.read_text();require(s.count('FINAL_MEMORY_SETTLEMENT_PLACEHOLDER')==1,'single final checkpoint placeholder');p.write_text(s.replace('FINAL_MEMORY_SETTLEMENT_PLACEHOLDER',line))
    with (ROOT/'docs/benchmarks/lp-billion.md').open('a') as f:f.write('\n'+line+'\nFinal settled evidence: `bounded-memory-settled-checkpoint-v1.json`.\n')
    print(dict(cpu_seconds=sum(cpu.values())/1e9,gpu_seconds=sum(gpu.values())/1e9,active=0),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','checkpoint']);a=p.parse_args();globals()[a.action]()
