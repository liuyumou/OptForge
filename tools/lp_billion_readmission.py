"""User-authorized recovery for one immutable overrun; every other overrun closes."""
from pathlib import Path
import time
from lp_billion_common import BASE,ROOT,load,ref,resolve,require,CPU_CAPS,GPU_CAPS
from lp_confirmation2_supervisor import same_process
IDENTITY='copt-capacity-64m-v1-1-copt-gpu-pdlp'
SHA='f4707c7a84827b2ad2953172afb69ead1f2b5845e1b1ec202a35085a43af9304'
CPU='operational-cpu-v20'
GPU='operational-gpu-v17'

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

def cleared(path,gpu,phase,identity):
    receipt=ref(path)
    require(Path(path).name==IDENTITY+'.settlement.json' and receipt['sha256']==SHA,'resource admission closed by unapproved overrun')
    approval=load(BASE/'approved-recovery-v1.json');cleanup=load(resolve(approval['cleanup']))
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
    names={'tools/lp_billion_common.py','tools/lp_billion_budget.py','tools/lp_billion_idle.py','tools/lp_billion_readmission.py'}
    bound=set()
    for item in load(resolve(reservation['source_manifest']))['sources']:
        if item['original']['path'] in names:resolve(item['original']);bound.add(item['original']['path'])
    require(bound==names,'complete resource-source readmission binding')
