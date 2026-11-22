"""Exact proposed fair-comparison allocation; no authorization is inferred."""
from lp_billion_common import BASE,ROOT,ref,resolve,require

CPU=dict(implementation=10000,native=26000,admission=72000,development=260000,reporting=200000,cleanup=2000)
GPU=dict(admission=12000,development=56000)
OLD_CPU=dict(implementation=10000,native=26000,admission=58000,development=162000,reporting=113000,cleanup=1000)
OLD_GPU=dict(admission=10000,development=34000)
ANSWER='Approve full comparison allocation'

def validate(extension,previous,cpu_caps,gpu_caps):
    require(extension['status']=='explicitly_authorized' and extension['user_answer']==ANSWER,'explicit full-comparison authorization')
    require(extension['previous_approval']==ref(BASE/'approved-assessment-extension-v1.json'),'complete preceding approval chain')
    require(previous['status']=='explicitly_authorized' and previous['user_answer']=='Approve assessment/control allocation','prior assessment authorization remains required')
    require(extension['original_approval']==previous['original_approval']==ref(BASE/'approved-recovery-v1.json'),'original recovery authorization remains required')
    require(extension['old_cpu_caps']==previous['cpu_caps']==OLD_CPU and extension['old_gpu_caps']==previous['gpu_caps']==OLD_GPU,'exact prior assessment caps')
    require(extension['cpu_caps']==cpu_caps==CPU and extension['gpu_caps']==gpu_caps==GPU,'exact approved fair-comparison caps')
    require(sum(cpu_caps.values())==570000 and sum(gpu_caps.values())==68000,'proposed totals unchanged')
    resolve(extension['protocol']);resolve(extension['proposal'])
    return True


def worksheet():
    phases=dict(implementation=240,native=0,admission=16680,development=113280,reporting=106600,cleanup=1080)
    gpu=dict(admission=3870,development=23400)
    require(sum(phases.values())==237880 and sum(gpu.values())==27270,'whole conservative comparison calculation')
    return dict(cpu=phases,gpu=gpu,cpu_caps=CPU,gpu_caps=GPU,
                proposal=ref(ROOT/'docs/specifications/SPEC-0046-amendment-79.md'))
