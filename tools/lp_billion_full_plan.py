"""Reviewable whole-roster reservation, before any billion scientific attempt."""
import argparse,math
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require,disk_bytes,DISK_LIMIT,NS
from lp_billion_budget import accounting
from lp_billion_campaign import endpoint_bytes
from lp_billion_memory_bounds_final import bounded_capacity
FAMILIES=['irregular','wide','tall','coupled_blocks','ill_scaled','degenerate']
LANES=['native','fp32','fp4x2','copt-cpu-auto','copt-gpu-pdlp']
# 600 s solver wall includes all preparation. Fresh-process reserves additionally
# cover original input, final work past a deadline, output and cleanup.
SOLVE={'irregular':900,'wide':1100,'tall':850,'coupled_blocks':700,'ill_scaled':900,'degenerate':900}
COPT={'irregular':900,'wide':1000,'tall':900,'coupled_blocks':800,'ill_scaled':900,'degenerate':900}
# Original billion construction checks take 138--317 s. These separate reserves
# include cold input and headroom; each additional distinct assessment reserves
# another check, with shared original input but no arithmetic shortcuts.
FINAL={'irregular':400,'wide':550,'tall':350,'coupled_blocks':250,'ill_scaled':400,'degenerate':400}
EXTRA={'irregular':250,'wide':400,'tall':250,'coupled_blocks':150,'ill_scaled':250,'degenerate':250}

def proposal(output):
    cpu,gpu=accounting();used_cpu=sum(cpu.values())/NS;used_gpu=sum(gpu.values())/NS
    models={f:load(BASE/f'models-1b-{f}-v1/result.json') for f in FAMILIES}
    disk=disk_bytes();candidates=[]
    for iterations in range(500,5001,500):
        cells=[]
        for f in FAMILIES:
            model=models[f]
            for lane in LANES:
                project=lane in LANES[:3]
                solve=SOLVE[f] if project else COPT[f]
                audit=FINAL[f]+math.ceil(iterations/500)*EXTRA[f] if project else FINAL[f]
                storage=endpoint_bytes(model,iterations) if project else 8*(model['columns']+2*model['rows'])
                cells.append(dict(family=f,lane=lane,solve_seconds=solve,audit_seconds=audit,
                    cpu_seconds=4*(solve+audit),gpu_seconds=solve if lane!='copt-cpu-auto' else 0,
                    endpoint_bytes_upper=storage,host_gib=bounded_capacity(model,lane)['host_gib'] if project else 128))
        prospective_cpu=sum(c['cpu_seconds'] for c in cells)
        prospective_gpu=sum(c['gpu_seconds'] for c in cells)
        storage=disk+sum(c['endpoint_bytes_upper'] for c in cells)+(8<<30)
        # Retain remaining admission/development tooling, final documentation and
        # cleanup allowance. Actual resource charges remain separately recorded.
        total_cpu=used_cpu+prospective_cpu+6000
        total_gpu=used_gpu+prospective_gpu+2000
        candidates.append(dict(iterations=iterations,cells=cells,science_and_audit_cpu_seconds=prospective_cpu,
            science_gpu_seconds=prospective_gpu,total_cpu_with_completion_reserve=total_cpu,
            total_gpu_with_completion_reserve=total_gpu,storage_bytes=storage,
            fits_original_allocation=total_cpu<=240000 and total_gpu<=30000 and storage<=DISK_LIMIT,
            fits_proposed_allocation=total_cpu<=320000 and total_gpu<=35000 and storage<=DISK_LIMIT))
    put(output,dict(status='proposal_only_not_authorized_not_frozen',source=ref(__file__),
        original_allocation=dict(cpu_seconds=240000,gpu_seconds=30000),
        requested_total_allocation=dict(cpu_seconds=320000,gpu_seconds=35000),
        used_cpu_seconds=used_cpu,used_gpu_seconds=used_gpu,common_solver_wall_seconds=600,
        physical_limits_unchanged=True,strict_tolerance=1e-9,candidates=candidates))
    for c in candidates:print({k:v for k,v in c.items() if k!='cells'},flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output');a=p.parse_args();proposal(a.output)
