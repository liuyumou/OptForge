"""User-authorized recovery for one immutable overrun; every other overrun closes."""
from pathlib import Path
import time
from lp_billion_common import BASE,ROOT,load,ref,resolve,require,CPU_CAPS,GPU_CAPS
from lp_confirmation2_supervisor import same_process
IDENTITY='copt-capacity-64m-v1-1-copt-gpu-pdlp'
SHA='f4707c7a84827b2ad2953172afb69ead1f2b5845e1b1ec202a35085a43af9304'
CPU='operational-cpu-v29'
GPU='operational-gpu-v23'

def validate_exception(path,receipt,approval,cleanup):
    require(Path(path).name==IDENTITY+'.settlement.json' and receipt['sha256']==SHA,'resource admission closed by unapproved overrun')
    require(approval['status']=='explicitly_authorized' and approval['settlement']==receipt,'specific overrun approval binding')
    require(approval['user_answer']=='Approve recovery and increased time','explicit recovery authorization')
    require(approval['cpu_caps']==CPU_CAPS and approval['gpu_caps']==GPU_CAPS,'authorized phase caps')
    require(cleanup['status']=='cleanup_verified' and cleanup['settlement']==receipt,'overrun cleanup binding')
    require(cleanup['identities'] and all(not x['still_live'] and not same_process(x['identity']) for x in cleanup['identities']),'owned process identity still live')

def passed(identity):
    path=BASE/'resources'/(identity+'.settlement.json')
    require(path.exists(),'fresh operational gate missing '+identity)
    s=load(path);require(s['status']=='passed' and s['cleanup_empty'] and not s['overrun'],'fresh operational gate failed '+identity)
    return path

def transfer_approval(approval, transfer):
    require(transfer['status']=='explicitly_authorized' and transfer['user_answer']=='Approve the phase transfer','explicit phase-transfer authorization')
    require(transfer['previous_approval']==ref(BASE/'approved-recovery-v1.json'),'phase-transfer previous approval binding')
    require(transfer['old_cpu_caps']==approval['cpu_caps'] and transfer['old_gpu_caps']==approval['gpu_caps'],'phase-transfer old caps')
    require(transfer['cpu_caps']==CPU_CAPS and transfer['gpu_caps']==GPU_CAPS,'phase-transfer new caps')
    require(sum(CPU_CAPS.values())==sum(approval['cpu_caps'].values())==320000 and sum(GPU_CAPS.values())==sum(approval['gpu_caps'].values())==35000,'phase-transfer unchanged totals')
    resolve(transfer['protocol']);resolve(transfer['proposal'])
    return dict(approval,cpu_caps=CPU_CAPS,gpu_caps=GPU_CAPS)

def revised_transfer_approval(approval, transfer, previous, cpu_caps=None, gpu_caps=None):
    cpu_caps=CPU_CAPS if cpu_caps is None else cpu_caps
    gpu_caps=GPU_CAPS if gpu_caps is None else gpu_caps
    require(transfer['status']=='explicitly_authorized' and transfer['user_answer']=='Approve revised phase transfer','explicit revised transfer authorization')
    require(transfer['previous_transfer']==ref(BASE/'approved-packing-transfer-v1.json') and transfer['original_approval']==ref(BASE/'approved-recovery-v1.json'),'revised transfer approval chain')
    require(previous['status']=='explicitly_authorized' and previous['user_answer']=='Approve the phase transfer' and previous['previous_approval']==transfer['original_approval'],'previous transfer authorization')
    require(previous['old_cpu_caps']==approval['cpu_caps'] and previous['old_gpu_caps']==approval['gpu_caps'],'original recovery caps retained')
    require(transfer['old_cpu_caps']==previous['cpu_caps'] and transfer['old_gpu_caps']==previous['gpu_caps'],'revised transfer old caps')
    require(transfer['cpu_caps']==cpu_caps and transfer['gpu_caps']==gpu_caps,'revised transfer new caps')
    require(sum(cpu_caps.values())==sum(previous['cpu_caps'].values())==sum(approval['cpu_caps'].values())==320000 and sum(gpu_caps.values())==sum(previous['gpu_caps'].values())==sum(approval['gpu_caps'].values())==35000,'revised transfer unchanged totals')
    for record in [transfer,previous]:resolve(record['protocol']);resolve(record['proposal'])
    return dict(approval,cpu_caps=cpu_caps,gpu_caps=gpu_caps)

def assessment_approval(approval, extension, revised, previous):
    require(extension['status']=='explicitly_authorized' and extension['user_answer']=='Approve assessment/control allocation','explicit assessment/control authorization')
    require(extension['previous_approval']==ref(BASE/'approved-packing-transfer-v2.json') and extension['original_approval']==ref(BASE/'approved-recovery-v1.json'),'assessment approval chain')
    require(extension['old_cpu_caps']==revised['cpu_caps'] and extension['old_gpu_caps']==revised['gpu_caps'],'assessment previous caps')
    revised_transfer_approval(approval,revised,previous,extension['old_cpu_caps'],extension['old_gpu_caps'])
    require(extension['cpu_caps']==CPU_CAPS and extension['gpu_caps']==GPU_CAPS,'assessment authorized exact phase caps')
    require(sum(CPU_CAPS.values())==370000 and sum(GPU_CAPS.values())==44000,'assessment authorized totals')
    resolve(extension['proposal']);resolve(extension['protocol'])
    return dict(approval,cpu_caps=CPU_CAPS,gpu_caps=GPU_CAPS)

def cleared(path,gpu,phase,identity):
    receipt=ref(path)
    require(Path(path).name==IDENTITY+'.settlement.json' and receipt['sha256']==SHA,'resource admission closed by unapproved overrun')
    approval=load(BASE/'approved-recovery-v1.json');cleanup=load(resolve(approval['cleanup']))
    if approval['cpu_caps']!=CPU_CAPS or approval['gpu_caps']!=GPU_CAPS:
        previous=load(BASE/'approved-packing-transfer-v1.json')
        revised=BASE/'approved-packing-transfer-v2.json'
        extension=BASE/'approved-assessment-extension-v1.json'
        approval=assessment_approval(approval,load(extension),load(revised),previous) if extension.exists() else (revised_transfer_approval(approval,load(revised),previous) if revised.exists() else transfer_approval(approval,previous))
    validate_exception(path,receipt,approval,cleanup);resolve(approval['protocol'])
    if not gpu and phase=='admission' and identity==CPU:return
    passed(CPU)
    if not gpu and phase in ['admission','reporting','cleanup']:return
    if gpu and phase=='admission' and identity==GPU:
        from lp_billion_availability import stable
        proof=load(BASE/'availability'/(GPU+'.json'))
        require(proof['status']=='observed_idle' and stable([load(resolve(p)) for p in proof['samples']],time.monotonic_ns()),'fresh complete idle window')
        return
    gate=passed(GPU)
    reservation=load(gate.with_name(GPU+'.reservation.json'))
    names={'tools/lp_billion_common.py','tools/lp_billion_budget.py','tools/lp_billion_idle.py','tools/lp_billion_readmission.py','tools/lp_billion_disk_inventory.c','tools/lp_billion_source_store.py'}
    bound=set()
    for item in load(resolve(reservation['source_manifest']))['sources']:
        if item['original']['path'] in names:resolve(item['original']);bound.add(item['original']['path'])
    require(bound==names,'complete resource-source readmission binding')
